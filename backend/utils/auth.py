import jwt
import uuid
import datetime
import os
import bcrypt
from functools import wraps
from flask import request, jsonify, g

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-key-change-this-in-prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 1

import redis

# ── Fix 3: Persistent JWT Revocation Denylist ───────────────────────────────
# Enforce Redis for high-availability production architectures
redis_client = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379"),
    socket_timeout=2,
    socket_connect_timeout=2,
    retry_on_timeout=True,
    decode_responses=True
)


def hash_password(password: str) -> str:
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    # Fix 3: Embed a unique JWT ID (jti) so individual tokens can be denylisted on logout
    to_encode.update({
        "exp": expire,
        "jti": str(uuid.uuid4()),  # Unique token fingerprint
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def revoke_token(token_jti: str):
    """Add a token's JTI to the revocation Redis blacklist with auto-expiry."""
    try:
        # Expire from blacklist naturally when token expires natively (1 hour)
        expiration_seconds = ACCESS_TOKEN_EXPIRE_HOURS * 3600
        redis_client.setex(f"denylist:{token_jti}", expiration_seconds, "true")
    except Exception as e:
        import logging
        logging.getLogger("DeepStegAI").error(f"Redis Denylist Error: {e}")
        # Fail open or closed depending on strictness. Here we just log.


# ── Fix 1 & 2: Concurrency-Safe Credit Deduction ────────────────────────────
def require_credits(cost_fixed=0, cost_per_unit=0, unit_field=None):
    """
    Concurrency-Safe Credit Decorator:
    1. Deduct credits upfront (uses atomic SELECT FOR UPDATE in CreditService).
    2. Execute the route (which might take 10 seconds for AI processing).
    3. If the route FAILS or returns 4xx/5xx, REFUND the credits (Rollback).
    This prevents concurrent requests from bypassing balance checks while avoiding long DB locks.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            from database.db import SessionLocal
            from services.credit_service import CreditService

            user_id_raw = getattr(request, 'user_id', None)
            email = getattr(request, 'user_email', None)

            if not user_id_raw:
                return jsonify({"error": "Authentication required"}), 401

            from uuid import UUID
            try:
                user_id = UUID(str(user_id_raw))
            except Exception:
                user_id = user_id_raw

            if email in ["aravalli813@gmail.com", "hjsudarshan18@gmail.com"]:
                return f(*args, **kwargs)

            total_cost = cost_fixed
            if cost_per_unit > 0 and unit_field:
                fields = [unit_field] if isinstance(unit_field, str) else unit_field
                unit_count = sum(len(request.files.getlist(field)) for field in fields)
                total_cost += (unit_count * cost_per_unit)

            # ── UPFRONT DEDUCTION (Phase 1) ──────────────────────────────────
            db = SessionLocal()
            request.credit_cost = total_cost
            request.credit_user_id = user_id
            try:
                new_balance = CreditService.deduct_credits(
                    db, user_id, total_cost, f"Service reservation: {request.path}"
                )
                if new_balance is None:
                    return jsonify({
                        "error": "Insufficient Neural Credits",
                        "required": total_cost,
                        "message": "Protocol rejected: Credit exhaustion detected."
                    }), 402
                request.updated_credits = new_balance
            except Exception as e:
                db.rollback()
                return jsonify({"error": f"Credit Matrix Error: {str(e)}"}), 500
            finally:
                db.close()

            # ── EXECUTE ROUTE ────────────────────────────────────────────────
            try:
                response = f(*args, **kwargs)
            except Exception as route_err:
                # ── REFUND ON EXCEPTION (Rollback Phase) ────────────────────
                db_refund = SessionLocal()
                try:
                    CreditService.add_credits(
                        db_refund, user_id, total_cost, "refund", "Service failed: Route Exception"
                    )
                finally:
                    db_refund.close()
                raise route_err

            # ── REFUND ON HTTP FAILURE (Rollback Phase) ─────────────────────
            status_code = response[1] if isinstance(response, tuple) else (
                response.status_code if hasattr(response, 'status_code') else 200
            )

            if not (200 <= status_code < 300):
                db_refund = SessionLocal()
                try:
                    CreditService.add_credits(
                        db_refund, user_id, total_cost, "refund", f"Service failed (HTTP {status_code})"
                    )
                    # We don't have the exact updated balance here easily, so we rely on client reload
                finally:
                    db_refund.close()
            else:
                # Success! Inject the updated credits into headers
                updated_credits = getattr(request, 'updated_credits', None)
                if updated_credits is not None:
                    if isinstance(response, tuple):
                        data, status = response[0], response[1]
                        headers = response[2] if len(response) > 2 else {}
                        headers['X-Updated-Credits'] = str(updated_credits)
                        return data, status, headers
                    elif hasattr(response, 'headers'):
                        response.headers['X-Updated-Credits'] = str(updated_credits)

            return response
        return decorated
    return decorator


# ── Fix 3: token_required checks denylist ────────────────────────────────────
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            auth_header = request.headers["Authorization"]
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

        if not token:
            return jsonify({"message": "Token is missing!"}), 401

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            # Check if this specific token was revoked (logout denylist in Redis)
            jti = payload.get("jti")
            if jti:
                try:
                    if redis_client.exists(f"denylist:{jti}"):
                         return jsonify({"message": "Token has been revoked. Please log in again."}), 401
                except Exception as e:
                    import logging
                    logging.getLogger("DeepStegAI").error(f"Redis Token Validation Error: {e}")
                    pass # Fail open if Redis drops entirely, or can fail closed depending on strictness.

            uid = payload.get("user_id")
            if uid:
                try:
                    request.user_id = uuid.UUID(uid)
                except:
                    request.user_id = uid
            request.user_email = payload.get("email")
            request.token_jti = jti  # Stash jti for logout endpoint to use

        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "Invalid token!"}), 401
        except Exception as e:
            return jsonify({"message": str(e)}), 401

        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = getattr(request, 'user_id', None)
        email = getattr(request, 'user_email', None)

        if not user_id:
            return jsonify({"message": "Authentication required for admin access"}), 401

        # Developer bypass
        if email in ["aravalli813@gmail.com", "hjsudarshan18@gmail.com"]:
            return f(*args, **kwargs)

        from database.db import SessionLocal
        from models.user import User
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user or user.role != "admin":
                return jsonify({"message": "Admin privileges required"}), 403
        finally:
            db.close()

        return f(*args, **kwargs)
    return decorated
