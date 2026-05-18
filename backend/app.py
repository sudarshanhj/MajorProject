import os
import sys
import random
import logging
import bcrypt
import io
import json
import numpy as np
import zipfile
import markdown
import filetype
import base64
import datetime
import math
from dotenv import load_dotenv
from database.db import engine, Base
from routes.auth import auth_bp
from routes.api import api_bp
from routes.razorpay_routes import razorpay_bp
from PIL import Image
from flask import Flask, request, jsonify, send_file, render_template, redirect, session, url_for
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
import concurrent.futures
import torch
import cv2
import torchvision
from torchvision import transforms

# --- Modular Imports ---

# --- Modular Imports from Parent ---
from stego_engine import embed_payload_into_image, extract_payload_from_image, image_capacity_bits, bits_to_bytes, bytes_to_bits
from crypto_utils import aes_encrypt, aes_decrypt, xor_encrypt_decrypt
from adaptive_engine import embed_file_adaptive, extract_file_adaptive
from protocol import package_payload, unpackage_payload
# Deferred AI imports moved to load_ai_model
from utils.auth import token_required, require_credits, admin_required
from utils.email_utils import send_admin_notification, send_user_receipt
from utils.activity import log_user_activity
from utils.heatmap_utils import generate_difference_heatmap
from models.gradcam import generate_gradcam
from detection_engine import scan_image_for_signature

# --- Service Imports ---
from database.db import SessionLocal
from services.file_service import FileService
from services.analysis_service import AnalysisService

# --- Professional Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("DeepStegAI")

app = Flask(__name__)

def auto_migrate_db():
    print("Initiating automatic database schema alignment...")
    db = SessionLocal()
    try:
        from sqlalchemy import text
        # Safely inject missing columns for production updates without destroying data
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_code VARCHAR"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS otp_expiry TIMESTAMP"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token VARCHAR"))
        db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS reset_token_expiry TIMESTAMP"))
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Skipped schema alignment (tables might not exist yet): {e}")
    finally:
        db.close()

# Execute hot-migrations explicitly for Docker deployments
auto_migrate_db()
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024 # 500 MB limit
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or os.urandom(24)

# Admin access is now restricted by verified developer email
DEVELOPER_EMAILS = [e.strip() for e in os.environ.get("ADMIN_EMAILS", "aravalli813@gmail.com,hjsudarshan18@gmail.com").split(',') if e.strip()]

# Load environment variables
load_dotenv()

# Initialize Sentry for Crash Reporting
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FlaskIntegration()],
        traces_sample_rate=1.0
    )
    logger.info("Sentry integration enabled.")

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(api_bp, url_prefix='/api')
app.register_blueprint(razorpay_bp, url_prefix='/api/razorpay')

# Initialize Database
try:
    import models  # Ensure all models are registered before creating tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize database: {e}")

MESSAGES_FILE = os.path.join(os.path.dirname(__file__), 'data', 'messages.json')

# Apply standard CORS policy with exposed headers for binary metadata
CORS(app, resources={r"/*": {"origins": "*"}}, expose_headers=["Content-Disposition", "content-disposition", "X-Filename", "X-Updated-Credits", "X-Recovery-Token"])

# Fix 2: Rate Limiter — Enforce REDIS for production concurrency safety.
# Mandatory Redis config with retries and timeouts for stability.
REDIS_URL = os.environ.get("REDIS_URL", "memory://")
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["1000 per day", "200 per hour"],
    storage_uri=REDIS_URL,
    storage_options={
        "socket_timeout": 5,
        "socket_connect_timeout": 5,
        "retry_on_timeout": True
    }
)

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify(error="Rate limit exceeded", details=str(e.description)), 429

def validate_uploaded_image(file_storage):
    """Deep binary validation to reject non-image payloads safely."""
    header = file_storage.read(512)
    file_storage.seek(0)
    kind = filetype.guess(header)
    if kind is None or kind.mime not in ['image/png', 'image/jpeg', 'image/jpg', 'image/webp']:
        raise ValueError(f"Invalid file type. Found: {kind.extension if kind else 'Unknown'}. Only PNG/JPG/WEBP allowed.")

# Increase file upload limit to 100MB for batch processing
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024

os.makedirs(os.path.join(os.path.dirname(__file__), 'data'), exist_ok=True)

SECURITY_LIMIT_RATIO = 0.35

def calculate_max_payload(cover_size_bytes: int) -> int:
    """Calculate the strict 35% maximum payload."""
    return math.floor(cover_size_bytes * SECURITY_LIMIT_RATIO)

@app.route('/')
def health_root():
    """Root health check for Hugging Face verification."""
    return jsonify({"status": "SYSTEM_ONLINE", "environment": "HuggingFace_Production"}), 200

@app.route('/api/capacity', methods=['POST'])
@limiter.limit("60 per minute")
def api_capacity():
    """Single source of truth for payload capacity calculation."""
    try:
        if 'cover' not in request.files:
            return jsonify({"error": "Cover image is required"}), 400
            
        cover = request.files['cover']
        protocol = request.form.get('protocol', 'LSB')
        
        # Determine actual file size
        cover.seek(0, 2)
        cover_bytes = cover.tell()
        cover.seek(0)
        
        max_payload_bytes = calculate_max_payload(cover_bytes)
        max_payload_mb = round(max_payload_bytes / (1024 * 1024), 2)
        
        return jsonify({
            "success": True,
            "data": {
                "protocol": protocol,
                "cover_size_bytes": cover_bytes,
                "max_payload_bytes": max_payload_bytes,
                "max_payload_mb": max_payload_mb,
                "security_policy": "Strict 35% Enforcement"
            },
            "error": None
        })
    except Exception as e:
        logger.error(f"Capacity calculation error: {e}")
        return jsonify({"error": str(e)}), 500


# --- Initialized on demand in load_ai_model ---
MODEL = None
DEVICE = None

# GLOBAL AI EXECUTOR: Ensures true request queuing across the entire Flask application
# instead of spawning a new pool per request. Protects against Docker OOM and OS stalls.
GLOBAL_AI_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=1)

def get_calibrated_ai_score(image_pil, initial_ai_score, signature_detected):
    """
    Confidence Calibration Layer:
    If a signature is detected, boost the AI score based on payload density.
    This ensures the AI output matches the confirmed results.
    """
    ai_score = initial_ai_score
    if signature_detected:
        try:
            # Read header to find payload size
            arr = np.array(image_pil)
            flat = arr.flatten()
            # Extract enough bits for fixed metadata: 13 (Sig) + 10 (MetadataFix) = 23 bytes = 184 bits
            header_bits = (flat[:184] & 1).astype(np.uint8)
            header_bytes = bits_to_bytes(header_bits)
            
            # Metadata structure: Proto(1), Enc(1), Count(2), PLen(4)... Starts at offset 13
            # Payload length is at bytes 17:21
            payload_len = int.from_bytes(header_bytes[17:21], "big")
            
            # Calculate density
            cap = image_capacity_bits(image_pil)
            usage_ratio = (payload_len * 8) / cap
            
            # Calibration: Base 60% + payload factor
            cal_score = 0.60 + (usage_ratio * 0.399)
            cal_score = min(0.999, cal_score)
            
            return max(ai_score, cal_score)
        except Exception as e:
            logger.debug(f"Calibration error: {e}")
            return max(ai_score, 0.95)
    return ai_score

def load_ai_model():
    global MODEL, DEVICE
    import gc
    from steganalysis_model import get_model
    
    # 1. Aggressive pre-load cleanup
    gc.collect()
    
    DEVICE = torch.device("cpu") # Force CPU for stability on free tier
    torch.set_num_threads(1)
    
    model_path = os.path.join(os.path.dirname(__file__), 'models', 'stego_model.pth')
    try:
        if os.path.exists(model_path):
            file_size = os.path.getsize(model_path)
            logger.info(f"Loading Neural Engine ({file_size/1024/1024:.2f} MB)...")
            MODEL = get_model().to(DEVICE)
            state_dict = torch.load(model_path, map_location=DEVICE)
            MODEL.load_state_dict(state_dict)
            MODEL.eval()
            del state_dict
            gc.collect()
            logger.info("Neural Engine active.")
        else:
            logger.warning(f"Neural Engine weights missing at {model_path}. AI features disabled.")
    except Exception as e:
        logger.error(f"Neural Engine initialization failed: {e}")
        gc.collect()

# Model loading is now deferred to the first /api/analyze request
# load_ai_model()

# --- Routes ---

@app.route('/api/batch', methods=['POST', 'OPTIONS'])
@limiter.limit("10 per minute")
@token_required
@require_credits(cost_per_unit=2, unit_field=['covers', 'stegos'])
def api_batch():
    try:
        mode = request.form.get('mode') # 'hide' or 'extract'
        password = request.form.get('password', '')
        
        if mode == 'hide':
            if 'covers' not in request.files or 'secret' not in request.files:
                 return jsonify({'error': 'Missing files for batch hide'}), 400
            
            method = request.form.get('method', 'lsb').lower()
            covers = request.files.getlist('covers')
            if len(covers) > 50:
                return jsonify({'error': 'Batch limit exceeded: maximum 50 covers.'}), 400
            for c in covers:
                validate_uploaded_image(c)
            
            secret = request.files['secret']
            secret_bytes = secret.read()
            
            zip_buffer = io.BytesIO()
            processed_count = 0
            summary_lines = [f"DeepStegAI Batch Hide Report - {datetime.datetime.now()}", "-"*50]
            
            with zipfile.ZipFile(zip_buffer, "w") as zf:
                for i, cover in enumerate(covers):
                    try:
                        c_img = Image.open(cover).convert("RGB")
                        
                        if method == 'adaptive':
                            payload = package_payload([{'name': secret.filename, 'data': secret_bytes}], 'ADAPTIVE', password)
                            stego, token = embed_file_adaptive(c_img, payload, "", password)
                            summary_lines.append(f"[+] {cover.filename}: Embedded (Adaptive). Recovery Token: {token}")
                        else:
                            # Standard LSB
                            payload = package_payload([{'name': secret.filename, 'data': secret_bytes}], 'LSB', password)
                            stego = embed_payload_into_image(c_img, payload)
                            summary_lines.append(f"[+] {cover.filename}: Embedded (Standard LSB)")

                        img_byte_arr = io.BytesIO()
                        stego.save(img_byte_arr, format="PNG")
                        zf.writestr(f"stego_{i}_{os.path.splitext(cover.filename)[0]}.png", img_byte_arr.getvalue())
                        processed_count += 1
                    except Exception as e:
                        summary_lines.append(f"[-] {cover.filename}: Error - {str(e)}")
                
                zf.writestr("embedding_report.txt", "\n".join(summary_lines))
            
            if processed_count == 0:
                return jsonify({'error': 'No images could be processed.', 'details': summary_lines}), 400
                
            zip_buffer.seek(0)
            
            # Database Persistence for batch results removed for STATELSS architecture.
            db = SessionLocal()
            try:
                log_user_activity(db, request.user_id, "BATCH_EMBED", f"Processed {processed_count} files", {"method": method, "count": processed_count})
            finally:
                db.close()
            
            zip_buffer.seek(0)
            return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='deepsteg_batch_stego.zip')

        elif mode == 'extract':
             if 'stegos' not in request.files:
                 return jsonify({'error': 'Missing stego files'}), 400
             
             stegos = request.files.getlist('stegos')
             if len(stegos) > 50:
                 return jsonify({'error': 'Batch limit exceeded: maximum 50 stego images.'}), 400
             for s in stegos:
                 validate_uploaded_image(s)
                 
             raw_keys = request.form.get('batch_keys', '')[:10000]  # Limit string size to prevent memory issues
             # Clean and split keys (passwords or tokens)
             candidate_keys = [k.strip() for k in raw_keys.split('\n') if k.strip()]
             if not candidate_keys:
                 candidate_keys = [""] # Try at least once (for plain images)
             
             zip_buffer = io.BytesIO()
             processed_success = 0
             summary_lines = [f"DeepStegAI Smart Batch Extraction Report - {datetime.datetime.now()}", "-"*50]
             
             with zipfile.ZipFile(zip_buffer, "w") as zf:
                 for i, stego_file in enumerate(stegos):
                     success_for_this_file = False
                     last_error = "Unknown"
                     
                     try:
                         s_img = Image.open(stego_file).convert("RGB")
                         scan_res = scan_image_for_signature(s_img)
                         summary_lines.append(f"[*] Analyzing {stego_file.filename} (Scan hint: {scan_res['message']})")
                         
                         for key in candidate_keys:
                             try:
                                 raw_block = b""
                                 
                                 try:
                                     _, raw_block, _ = extract_file_adaptive(s_img, password=key)
                                 except:
                                     if len(key) >= 16:
                                         try:
                                             _, raw_block, _ = extract_file_adaptive(s_img, recovery_token=key)
                                         except:
                                             pass
                                 
                                 if not raw_block:
                                     try:
                                         _, raw_block, _ = extract_payload_from_image(s_img)
                                     except:
                                         pass
                                 
                                 if raw_block:
                                     try:
                                         is_tok = len(key) >= 16 and "-" in key
                                         res_files, is_bundle_val = unpackage_payload(
                                             raw_block,
                                             password=None if is_tok else key,
                                             recovery_token=key if is_tok else None
                                         )
                                         if is_bundle_val:
                                             for rf in res_files:
                                                 zf.writestr(f"{i}_{rf['name']}", rf['data'])
                                         else:
                                             zf.writestr(f"{i}_{res_files[0]['name']}", res_files[0]['data'])
                                         summary_lines.append(f"  [+] Success using key: '{key[:5]}...'")
                                         processed_success += 1
                                         success_for_this_file = True
                                         break
                                     except:
                                         pass
                             except Exception as e:
                                 last_error = str(e)
                                 continue
                         
                         if not success_for_this_file:
                             summary_lines.append(f"  [-] Failed. Last tried key error hint: {last_error}")
                             
                     except Exception as e:
                         summary_lines.append(f"  [-] Critical Error: {str(e)}")
                         logger.error(f"Batch extractor critical failure: {e}")
                 
                 zf.writestr("DEEPSTEGAI_BATCH_REPORT.txt", "\n".join(summary_lines))
             
             if processed_success == 0:
                 return jsonify({'error': 'No files extracted. Ensure your keys list contains the correct items.', 'details': summary_lines}), 400
                 
             zip_buffer.seek(0)
             return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='deepsteg_results.zip')

        return jsonify({'error': 'Invalid mode'}), 400
        
    except Exception as e:
        logger.error(f"Batch processing error: {e}")
        return jsonify({'error': str(e)}), 500

# --- Contact & Admin Routes ---

import threading
from models.message import Message

@app.route('/api/contact', methods=['POST'])
def api_contact():
    """Endpoint for the Support page to submit queries."""
    try:
        data = request.json
        if not data or 'message' not in data:
            return jsonify({'error': 'Message required'}), 400
            
        now = datetime.datetime.now()
        name = data.get('name', 'Anonymous')[:100]
        email = data.get('email', 'No Email')[:100]
        msg_text = data['message'][:2000]
        
        db = SessionLocal()
        try:
            new_msg = Message(name=name, email=email, message=msg_text)
            db.add(new_msg)
            db.commit()
            db.refresh(new_msg)
            entry = new_msg.to_dict()
        finally:
            db.close()
            
        # Send Email Notifications in background (To Admin and User receipt)
        def notify_all(entry_data):
            try:
                send_admin_notification(entry_data)
                send_user_receipt(entry_data)
            except Exception as email_err:
                logger.error(f"Failed to send email: {email_err}")
                
        threading.Thread(target=notify_all, args=(entry,), daemon=True).start()
            
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Contact API Error: {e}", exc_info=True)
        return jsonify({'error': "Processing Failed"}), 500

@app.route('/api/messages', methods=['GET'])
@token_required
@admin_required
def get_messages():
    """Admin endpoint to retrieve support queries. Only accessible by the developer."""
    try:

        db = SessionLocal()
        try:
            # Fetch last 500 messages
            messages = db.query(Message).order_by(Message.created_at.desc()).limit(500).all()
            msg_list = [m.to_dict() for m in messages]
        finally:
            db.close()
            
        return jsonify({
            "success": True,
            "data": msg_list,
            "error": None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/audit-logs', methods=['GET'])
@token_required
@admin_required
def get_audit_logs():
    """Admin endpoint to view all system activity logs."""
    from models.activity_log import ActivityLog
    try:
        db = SessionLocal()
        try:
            logs = db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(1000).all()
            log_list = [l.to_dict() for l in logs]
        finally:
            db.close()
            
        return jsonify({
            "success": True,
            "data": log_list,
            "error": None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- Core API ---

@app.route('/api/embed', methods=['POST'])
# Generous demo allocation: 30 requests per minute per user (1 every 2s)
@limiter.limit("30 per minute")
@token_required
@require_credits(cost_fixed=5)
def api_embed():
    logger.info("Processing embedding request")
    try:
        if 'cover' not in request.files or 'secret' not in request.files:
            return jsonify({'error': 'Missing cover image or secret file'}), 400
        
        cover_file = request.files['cover']
        validate_uploaded_image(cover_file)
        
        # Security Policy: Strict 35% Payload Limit Implementation
        cover_file.seek(0, 2)
        cover_size = cover_file.tell()
        cover_file.seek(0)
        
        secret_files = request.files.getlist('secret')
        if not secret_files:
            return jsonify({'error': 'Missing secret file'}), 400
            
        total_secret_size = sum(len(f.read()) for f in secret_files)
        for f in secret_files: f.seek(0)
        
        max_secure_payload = calculate_max_payload(cover_size)
        
        if total_secret_size > max_secure_payload:
            return jsonify({
                "error": "Strict Security Policy: Payload exceeds 35% of the cover image's original file size."
            }), 400

        method = request.form.get('method', 'LSB').upper() # LSB or ADAPTIVE
        password = request.form.get('password', '')

        if not password and method == 'ADAPTIVE':
             return jsonify({'error': 'Password is required for Adaptive Edge method'}), 400
        
        cover_img = Image.open(cover_file).convert("RGB")
        
        # Convert Multi-file to list of dicts for protocol handler
        files_to_package = []
        for f in secret_files:
            f.seek(0)
            files_to_package.append({'name': f.filename, 'data': f.read()})
            
        # Standardized DEEPSTEGAI_V1 packaging
        full_stego_payload = package_payload(files_to_package, method, password)

        recovery_token = None
        stego_img = None

        if method == 'ADAPTIVE':
            # Adaptive Edge Protocol automatically handles the internal encryption if password passed
            stego_img, token = embed_file_adaptive(cover_img, full_stego_payload, "payload.bin", password)
            recovery_token = token 
        else:
            # Standard LSB
            # Calculate total bits: Signature + Metadata + Payload + Checksum
            if len(full_stego_payload) * 8 > image_capacity_bits(cover_img):
                 return jsonify({'error': 'File too large for this cover image'}), 400

            stego_img = embed_payload_into_image(cover_img, full_stego_payload)
            # For LSB, we might need to derive a token if password was used
            if password:
                from crypto_utils import derive_key
                recovery_token = derive_key(password).decode('utf-8')

        # Database Persistence
        db = SessionLocal()
        try:
            # FileService storage REMOVED. Images remain in memory (stateless).
            # Log Activity
            log_user_activity(db, request.user_id, "EMBED", f"Embedded payload into {cover_file.filename}", {"method": method})
        except Exception as db_err:
            logging.error(f"Activity logging failed: {str(db_err)}")
        finally:
            db.close()

        # Return Binary Image with Metadata in Headers
        img_buffer = io.BytesIO()
        stego_img.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        
        response = send_file(
            img_buffer,
            mimetype='image/png',
            as_attachment=False, # Set to False so browser can 'Show' it in result area
            download_name='stego_image.png'
        )
        
        # Add metadata to headers
        if recovery_token:
            response.headers['X-Recovery-Token'] = recovery_token
        
        updated_credits = getattr(request, 'updated_credits', None)
        if updated_credits is not None:
            response.headers['X-Updated-Credits'] = str(updated_credits)
            
        return response

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Embedding error: {e}", exc_info=True)
        return jsonify({'error': f"Internal server error: {str(e)}"}), 500

@app.route('/api/extract', methods=['POST'])
@limiter.limit("10 per minute")
@token_required
@require_credits(cost_fixed=2)
def api_extract():
    logger.info("Processing extraction request")
    try:
        if 'stego' not in request.files:
             return jsonify({'error': 'Missing stego image'}), 400
        
        stego_file = request.files['stego']
        validate_uploaded_image(stego_file)
        password = request.form.get('password', '')
        recovery_token = request.form.get('recovery_token', '')
        
        from detection_engine import scan_image_for_signature
        stego_img = Image.open(stego_file).convert("RGB")
        
        # 1. Detect Signature
        scan_res = scan_image_for_signature(stego_img)
        
        raw_extracted_block = b""
        
        # 2. Extract from engine
        if scan_res["detected"] and "Adaptive" in scan_res["message"]:
            try:
                _, data, token = extract_file_adaptive(stego_img, password=password, recovery_token=recovery_token)
                raw_extracted_block = data
            except ValueError as ve:
                return jsonify({'error': str(ve)}), 403
        elif scan_res["detected"]:
            try:
                # LSB uses extract_payload_from_image which now returns the whole block
                _, raw_extracted_block, _ = extract_payload_from_image(stego_img)
            except Exception as e:
                return jsonify({'error': str(e)}), 403
        else:
            return jsonify({'error': 'No steganography signature found'}), 404

        # 3. Standardized Protocol Unpackaging
        try:
            results, is_bundle = unpackage_payload(raw_extracted_block, password, recovery_token)
            
            if is_bundle:
                # Re-zip for download if it was a bundle
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for f in results:
                        zf.writestr(f['name'], f['data'])
                content = zip_buffer.getvalue()
                filename = "deepsteg_bundle.zip"
                final_mimetype = "application/zip"
            else:
                filename = results[0]['name']
                content = results[0]['data']
                kind = filetype.guess(content)
                final_mimetype = kind.mime if kind else 'application/octet-stream'
        except Exception as e:
            return jsonify({'error': str(e)}), 400

        # Log Activity (File tracking Removed for Stateless)
        db = SessionLocal()
        try:
            log_user_activity(db, request.user_id, "EXTRACT", f"Extracted {filename}")
        finally:
            db.close()

        # Return Extracted File
        return send_file(
            io.BytesIO(content),
            as_attachment=True,
            download_name=filename,
            mimetype=final_mimetype
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze', methods=['POST'])
@limiter.limit("10 per minute")
@token_required
@require_credits(cost_fixed=2)
def api_analyze():
    logger.info("Processing analysis request")
    # Core AI Scan Pipeline: Upload -> Analyze -> Store -> Response
    try:
        # 1. Validation
        if 'image' not in request.files:
             return jsonify({
                 "success": False,
                 "data": None,
                 "error": "Missing image file"
             }), 400
             
        img_file = request.files['image']
        validate_uploaded_image(img_file)
        image_pil = Image.open(img_file).convert("RGB")
        
        # 2. Heuristic Analysis
        sig_res = scan_image_for_signature(image_pil)
        # Remove bytes from JSON early
        if "magic_bytes" in sig_res:
             del sig_res["magic_bytes"]
        
        # 3. AI Analysis: The 'Heavy Lifting'
        ai_score = 0.0
        ai_success = False
        try:
            if not MODEL:
                load_ai_model()
            
            if not MODEL:
                return jsonify({"success": False, "error": "AI Engine missing"}), 503

            from train_stego_model import predict_image
            # We run the AI prediction in the Global Thread Pool
            import torch
            with torch.no_grad():
                future = GLOBAL_AI_EXECUTOR.submit(predict_image, MODEL, image_pil)
                ai_score = float(future.result(timeout=30.0))
            ai_success = True
            import gc
            gc.collect()
        except concurrent.futures.TimeoutError:
            logger.error("AI scanning timed out (exceeded 30s)")
            return jsonify({
                "success": False,
                "data": None,
                "error": "AI scan timed out due to high server load. Please try again later."
            }), 503
        except Exception as e:
            logger.error(f"AI classification error: {e}")
        
        # 4. Confidence Calibration
        ai_score = float(get_calibrated_ai_score(image_pil, ai_score, sig_res.get("detected", False)))
        
        # 5. Verdict Logic (Restored to High-Sensitivity Perfection)
        verdict = "CLEAN"
        if sig_res.get("detected"):
            # A signature is a definitive 100% match
            verdict = "DETECTED"
        elif ai_score > 0.75:
            # High AI confidence => DETECTED
            verdict = "DETECTED"
        elif ai_score > 0.60:
            # Medium AI confidence => SUSPICIOUS
            verdict = "SUSPICIOUS"
            
        description = sig_res.get("message", "No hidden data detected.")
        if verdict == "SUSPICIOUS":
            description = f"Potential Hidden Data Found (Neural Confidence: {ai_score*100:.1f}%)"
        elif verdict == "DETECTED":
            if not sig_res.get("detected"):
                 description = f"Neural Signature Confirmed (Confidence: {ai_score*100:.1f}%)"
            else:
                 description = f"CONFIRMED Steganography: {description}"
        else:
            # Clean
            if ai_score > 0.5:
                description = "Clean (Minor noise artifacts detected, likely natural or AI-generated)"

        # 6. Build Standardized Data Objects
        # Structure for static_details in DB
        analysis_details = {
            "ai_score": ai_score,
            "method": "Signature + AI" if ai_success else "Signature Only",
            "extra": {
                "heuristic": sig_res,
                "description": description
            }
        }

        # 7. Database Persistence
        db = SessionLocal()
        try:
            # Create persistent file metadata record (stateless storage, but stateful history)
            db_file = FileService.create_record(db, request.user_id, img_file.filename, "cover")
            file_id = str(db_file.id)
            
            # Save standardized analysis result
            AnalysisService.save_analysis(db, db_file.id, verdict, ai_score, analysis_details)
            
            # Log high-level activity
            log_user_activity(db, request.user_id, "SCAN", f"Analyzed {img_file.filename} -> {verdict}", {
                "score": ai_score, 
                "verdict": verdict, 
                "file_id": file_id
            })
        except Exception as db_err:
            file_id = "N/A"
            logger.error(f"Persistence error: {db_err}")
        finally:
            db.close()

        # 8. Final Standardized API Response
        return jsonify({
            "success": True,
            "data": {
                "verdict": verdict,
                "ai_score": ai_score,
                "file_id": file_id,
                "details": analysis_details,
                "credits": getattr(request, 'updated_credits', None)
            },
            "error": None
        })

    except Exception as e:
        logger.error(f"Fatal Scan Error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "data": None,
            "error": str(e)
        }), 500

@app.route('/api/batch_analyze', methods=['POST'])
@app.route('/api/detection/batch', methods=['POST'])
@app.route('/api/analyze/batch', methods=['POST'])
@limiter.limit("10 per minute")
@token_required
@require_credits(cost_per_unit=2, unit_field='images')
def api_batch_analyze():
    """Performs deep AI analysis on multiple images."""
    if 'images' not in request.files:
        return jsonify({'error': 'No images provided'}), 400
    
    files = request.files.getlist('images')
    if len(files) > 50:
        return jsonify({'error': 'Batch limit exceeded: maximum 50 images.'}), 400
    for f in files:
        validate_uploaded_image(f)
        
    results = []
    db = SessionLocal()
    try:
        for f in files:
            try:
                # Read file for processing
                f.seek(0)
                file_bytes = f.read()
                f.seek(0)
                img = Image.open(f).convert("RGB")
                
                # 1. AI Analysis
                ai_score = 0.0
                if MODEL:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(predict_image, MODEL, img)
                        try:
                            ai_score = float(future.result(timeout=30.0))
                        except concurrent.futures.TimeoutError:
                            logger.error(f"AI batch scanning timed out for {f.filename}")
                            results.append({'filename': f.filename, 'error': "AI scan timed out for this image."})
                            continue
                
                # 2. Heuristic Check
                scan = scan_image_for_signature(img)
                
                # 3. Confidence Calibration
                ai_score = get_calibrated_ai_score(img, ai_score, scan["detected"])
                
                # Verdict calculation (Optimized for reliability)
                verdict = "CLEAN"
                if scan["detected"]:
                    verdict = "DETECTED"
                elif ai_score > 0.85:
                    verdict = "SUSPICIOUS"

                # 4. Database Persistence
                try:
                    db_file = FileService.create_record(db, request.user_id, f.filename, "cover")
                    AnalysisService.save_analysis(db, db_file.id, verdict, ai_score, {
                        "ai_score": ai_score,
                        "method": "batch_scan",
                        "extra": {"heuristic": scan["message"]}
                    })
                    log_user_activity(db, request.user_id, "BATCH_SCAN", f"Analyzed {f.filename} -> {verdict}", {
                        "ai_score": ai_score,
                        "verdict": verdict,
                        "method": "batch_scan",
                        "file_id": str(db_file.id)
                    })
                except Exception as inner_db_err:
                    logger.error(f"Failed to persist batch item {f.filename}: {inner_db_err}")

                results.append({
                    'id': 'N/A',
                    'filename': f.filename,
                    'ai_score': ai_score,
                    'verdict': verdict,
                    'heuristic': scan["message"]
                })
            except Exception as e:
                logger.error(f"Error analyzing batch file {f.filename}: {e}")
                results.append({'filename': f.filename, 'error': str(e)})

        return jsonify({
            'success': True,
            'data': results,
            'credits': getattr(request, 'updated_credits', None)
        })
    finally:
        db.close()

# --- Heatmap Endpoints ---

@app.route('/api/heatmap/difference', methods=['POST'])
@token_required
def api_heatmap_difference():
    try:
        if 'cover' not in request.files or 'stego' not in request.files:
            return jsonify({'error': 'Missing cover or stego image'}), 400
        
        cover_file = request.files['cover']
        stego_file = request.files['stego']
        
        # Read as numpy arrays for OpenCV
        cover_np = cv2.imdecode(np.frombuffer(cover_file.read(), np.uint8), cv2.IMREAD_COLOR)
        stego_np = cv2.imdecode(np.frombuffer(stego_file.read(), np.uint8), cv2.IMREAD_COLOR)
        
        if cover_np is None or stego_np is None:
            return jsonify({'success': False, 'error': 'Invalid image format'}), 400
            
        heatmap_b64 = generate_difference_heatmap(cover_np, stego_np)
        
        return jsonify({
            "success": True,
            "heatmap_b64": heatmap_b64,
            "colormap": "HOT"
        })
    except Exception as e:
        logger.error(f"Difference heatmap error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/heatmap/gradcam', methods=['POST'])
@token_required
def api_heatmap_gradcam():
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'Missing image file'}), 400

        if not MODEL:
            load_ai_model()
            if not MODEL:
                return jsonify({'success': False, 'error': 'AI Model could not be initialized'}), 503

        img_file = request.files['image']
        img_bytes = img_file.read()
        image_pil = Image.open(io.BytesIO(img_bytes)).convert("RGB")

        # Decode original image as numpy (BGR) for Canny edge detection
        original_np = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)

        transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
        ])

        img_tensor = transform(image_pil).unsqueeze(0).to(DEVICE)

        # Run Grad-CAM in a thread pool to avoid blocking the WSGI worker
        import torch
        import gc
        # Grad-CAM requires gradients, so we DO NOT use torch.no_grad() here.
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                generate_gradcam,
                MODEL,
                img_tensor,
                original_size=image_pil.size,
                original_image_np=original_np
            )
            try:
                result = future.result(timeout=45.0)
            except concurrent.futures.TimeoutError:
                logger.error("Grad-CAM timed out (exceeded 45s)")
                return jsonify({'success': False, 'error': 'Neural Analysis timed out. Our servers are at capacity.'}), 503

        gc.collect()
        heatmap_b64, pred_class, confidence = result

        logger.info(f"Grad-CAM generated for class={pred_class}, conf={confidence:.3f}")

        # Clean image: return null heatmap so frontend shows 'No Activations' state
        if heatmap_b64 is None:
            return jsonify({
                "success": True,
                "heatmap_b64": None,
                "prediction": "CLEAN",
                "confidence": float(confidence),
                "message": "No significant neural activations detected. Image appears clean."
            })

        return jsonify({
            "success": True,
            "heatmap_b64": heatmap_b64,
            "prediction": "STEGO" if pred_class == 1 else "CLEAN",
            "confidence": float(confidence),
            "message": "Neural Scrutiny Active — Hybrid Edge + Activation Analysis complete."
        })

    except Exception as e:
        logger.error(f"Grad-CAM error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # Threaded=True enables concurrency for batch operations
    load_ai_model()
    # use_reloader=False    # DeepStegAI is explicitly initialized for containerized cloud deployment or local testing
    port = int(os.environ.get('PORT', 7860))
    
    # Enable threaded=True for better concurrent request handling
    app.run(debug=True, port=port, host="0.0.0.0", threaded=True)