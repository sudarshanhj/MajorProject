from flask import Blueprint, request, jsonify
from pydantic import ValidationError
from database.db import SessionLocal
from models.user import User
from schemas.user import UserSignUp, UserLogin
from utils.auth import hash_password, verify_password, create_access_token, token_required, revoke_token
from sqlalchemy.exc import IntegrityError
import secrets
import datetime
from utils.email_utils import send_password_reset_email

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Validate input using Pydantic
        user_data = UserSignUp(**data)
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 422

    db = SessionLocal()
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            return jsonify({
                "success": False,
                "data": None,
                "error": "Email already registered"
            }), 400

        # Create new user
        new_user = User(
            email=user_data.email,
            password_hash=hash_password(user_data.password),
            credits=50,
            is_verified=False
        )
        
        # Generate OTP
        otp = str(secrets.randbelow(900000) + 100000) # 6 digits
        new_user.otp_code = otp
        new_user.otp_expiry = datetime.datetime.now() + datetime.timedelta(minutes=10)
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Send OTP
        from utils.email_utils import send_otp_email
        send_otp_email(new_user.email, otp)

        return jsonify({
            "success": True,
            "data": {
                "message": "User created. Please check your email for the OTP.",
                "user_id": str(new_user.id),
                "requires_verification": True
            },
            "error": None
        }), 201

    except IntegrityError:
        db.rollback()
        return jsonify({
            "success": False,
            "data": None,
            "error": "Could not create user"
        }), 500
    except Exception as e:
        db.rollback()
        return jsonify({
            "success": False,
            "data": None,
            "error": str(e)
        }), 500
    finally:
        db.close()

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        # Validate input
        login_data = UserLogin(**data)
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 422

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == login_data.email).first()
        
        if not user or not verify_password(login_data.password, user.password_hash):
            return jsonify({
                "success": False,
                "data": None,
                "error": "Invalid email or password"
            }), 401
            
        if not getattr(user, 'is_verified', True):
            # Resend OTP
            otp = str(secrets.randbelow(900000) + 100000)
            user.otp_code = otp
            user.otp_expiry = datetime.datetime.now() + datetime.timedelta(minutes=10)
            db.commit()
            from utils.email_utils import send_otp_email
            send_otp_email(user.email, otp)
            
            return jsonify({
                "success": False,
                "data": {"requires_verification": True, "email": user.email},
                "error": "Email not verified. A new OTP has been sent."
            }), 403

        # Generate JWT token
        access_token = create_access_token(data={
            "user_id": str(user.id),
            "email": user.email
        })

        return jsonify({
            "success": True,
            "data": {
                "access_token": access_token,
                "token_type": "bearer",
                "user": user.to_dict()
            },
            "error": None
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "data": None,
            "error": str(e)
        }), 500
@auth_bp.route('/verify-email', methods=['POST'])
def verify_email():
    data = request.get_json()
    if not data or 'email' not in data or 'otp' not in data:
        return jsonify({"error": "Email and OTP are required"}), 400
        
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == data['email']).first()
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404
            
        if user.is_verified:
            return jsonify({"success": True, "message": "User already verified"}), 200
            
        if user.otp_code != data['otp'] or not user.otp_expiry or user.otp_expiry < datetime.datetime.now():
            return jsonify({"success": False, "error": "Invalid or expired OTP"}), 400
            
        # Verify user
        user.is_verified = True
        user.otp_code = None
        user.otp_expiry = None
        db.commit()
        
        # Auto-login upon verification
        access_token = create_access_token(data={
            "user_id": str(user.id),
            "email": user.email
        })
        
        return jsonify({
            "success": True,
            "data": {
                "message": "Email verified successfully.",
                "access_token": access_token,
                "token_type": "bearer",
                "user": user.to_dict()
            },
            "error": None
        }), 200
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        db.close()

@auth_bp.route('/me', methods=['GET'])
@token_required
def get_current_user():
    from models.user import User
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == request.user_id).first()
        if not user:
             return jsonify({
                 "success": False,
                 "data": None,
                 "error": "User not found"
             }), 404
             
        return jsonify({
            "success": True,
            "data": user.to_dict(),
            "error": None
        }), 200
    finally:
        db.close()

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({"error": "Email is required"}), 400
        
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            # Generate secure token
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expiry = datetime.datetime.now() + datetime.timedelta(hours=1)
            db.commit()
            
            # Send email
            send_password_reset_email(user.email, token)
            
        # Always return success to prevent email enumeration
        return jsonify({"message": "If this email is registered, a reset link has been sent."}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('password')
    
    if not token or not new_password:
        return jsonify({"error": "Token and new password are required"}), 400
        
    db = SessionLocal()
    try:
        user = db.query(User).filter(
            User.reset_token == token,
            User.reset_token_expiry > datetime.datetime.now()
        ).first()
        
        if not user:
            return jsonify({"error": "Invalid or expired token"}), 400
            
        # Update password
        user.password_hash = hash_password(new_password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.commit()
        
        return jsonify({"message": "Password updated successfully"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({
            "success": False,
            "data": None,
            "error": str(e)
        }), 500
    finally:
        db.close()


@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout():
    """
    Fix 3 — JWT Revocation on Logout:
    Adds the current token's JTI to the in-memory denylist.
    Future requests using the same token will immediately receive 401.
    """
    jti = getattr(request, 'token_jti', None)
    if jti:
        revoke_token(jti)
    return jsonify({
        "success": True,
        "message": "Logged out successfully. Token has been invalidated."
    }), 200
