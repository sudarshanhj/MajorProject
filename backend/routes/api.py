from flask import Blueprint, jsonify, request
from sqlalchemy import text
from utils.auth import token_required
from database.db import SessionLocal
from services.file_service import FileService
from services.credit_service import CreditService
from services.analysis_service import AnalysisService

api_bp = Blueprint('api', __name__)

@api_bp.route('/health', methods=['GET'])
def health_check():
    db = SessionLocal()
    try:
        # Pre-warm the serverless database connection
        db.execute(text("SELECT 1"))
        return jsonify({"status": "ok", "db": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "error", "db": str(e)}), 500
    finally:
        db.close()

@api_bp.route('/files', methods=['GET'])
@token_required
def list_files():
    db = SessionLocal()
    try:
        files = FileService.get_user_files(db, request.user_id)
        return jsonify({
            "success": True,
            "data": [f.to_dict() for f in files],
            "error": None
        })
    finally:
        db.close()

@api_bp.route('/credits', methods=['GET'])
@token_required
def get_credits():
    from models.user import User
    from models.credit_transaction import CreditTransaction
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == request.user_id).first()
        transactions = db.query(CreditTransaction).filter(CreditTransaction.user_id == request.user_id).order_by(CreditTransaction.created_at.desc()).limit(20).all()
        return jsonify({
            "success": True,
            "data": {
                "credits": user.credits,
                "transactions": [t.to_dict() for t in transactions]
            },
            "error": None
        })
    finally:
        db.close()

@api_bp.route('/analysis', methods=['GET'])
@token_required
def list_analysis():
    db = SessionLocal()
    try:
        results = AnalysisService.get_user_analyses(db, request.user_id)
        return jsonify({
            "success": True,
            "data": [r.to_dict() for r in results],
            "error": None
        })
    finally:
        db.close()

@api_bp.route('/analysis/<file_id>', methods=['GET'])
@token_required
def get_analysis(file_id):
    import uuid
    db = SessionLocal()
    try:
        analysis = AnalysisService.get_analysis_by_file(db, uuid.UUID(file_id))
        if not analysis:
            return jsonify({
                "success": False,
                "data": None,
                "error": "Analysis not found"
            }), 404
        return jsonify({
            "success": True,
            "data": analysis.to_dict(),
            "error": None
        })
    finally:
        db.close()

@api_bp.route('/activity', methods=['GET'])
@token_required
def get_activity():
    from models.activity_log import ActivityLog
    db = SessionLocal()
    try:
        logs = db.query(ActivityLog).filter(ActivityLog.user_id == request.user_id).order_by(ActivityLog.created_at.desc()).limit(50).all()
        return jsonify({
            "success": True,
            "data": [l.to_dict() for l in logs],
            "error": None
        })
    finally:
        db.close()

@api_bp.route('/stats/global', methods=['GET'])
def get_global_stats():
    from models.activity_log import ActivityLog
    db = SessionLocal()
    try:
        # Aggregate all types of forensic and analysis activity
        logs = db.query(ActivityLog).filter(ActivityLog.action.in_(['SCAN', 'BATCH_SCAN', 'AI_SCAN', 'ANALYZE', 'FORENSIC_SCAN'])).all()
        total_scans = len(logs)
        
        # Proper check of metadata_json for verdict flags
        threats_found = 0
        for l in logs:
            meta = l.metadata_json or {}
            verdict = meta.get('verdict')
            
            # Fallback: Parse from description string if metadata is missing (for older logs)
            if not verdict and l.details:
                if "DETECTED" in l.details.upper():
                    verdict = "DETECTED"
                elif "SUSPICIOUS" in l.details.upper():
                    verdict = "SUSPICIOUS"
            
            if verdict and verdict.upper() in ['DETECTED', 'SUSPICIOUS']:
                threats_found += 1
        
        return jsonify({
            "success": True,
            "data": {
                "total_scans": total_scans,
                "threats_found": threats_found
            },
            "error": None
        })
    finally:
        db.close()
