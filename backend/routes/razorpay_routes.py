import os
import hmac
import hashlib
import razorpay
from flask import Blueprint, request, jsonify
from database.db import SessionLocal
from models.user import User
from models.razorpay_transaction import RazorpayTransaction
from services.credit_service import CreditService
from utils.auth import token_required
from utils.activity import log_user_activity
import logging
import uuid

logger = logging.getLogger("DeepStegAI.Razorpay")

razorpay_bp = Blueprint('razorpay', __name__)

# Lazy-initialized Razorpay client (env vars aren't available at import time)
_client = None

def get_razorpay_client():
    """Returns the Razorpay client, initializing it on first call."""
    global _client
    if _client is None:
        key_id = os.environ.get("RAZORPAY_KEY_ID", "")
        key_secret = os.environ.get("RAZORPAY_KEY_SECRET", "")
        if not key_id or not key_secret:
            raise RuntimeError("RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET must be set in .env")
        _client = razorpay.Client(auth=(key_id, key_secret))
        logger.info(f"Razorpay client initialized with key: {key_id[:12]}...")
    return _client

def get_razorpay_key_id():
    return os.environ.get("RAZORPAY_KEY_ID", "")

def get_razorpay_key_secret():
    return os.environ.get("RAZORPAY_KEY_SECRET", "")

# Pricing Tiers: amount_inr -> credits
PRICING_TIERS = {
    99: 50,    # ₹99  -> 50 credits
    199: 120,  # ₹199 -> 120 credits
    499: 350   # ₹499 -> 350 credits
}


# ─── HELPER: Idempotency Check ───────────────────────────────────────────────
def _is_payment_already_processed(db, payment_id: str) -> bool:
    """Returns True if this payment_id was already recorded (prevents double-crediting)."""
    return db.query(RazorpayTransaction).filter_by(razorpay_payment_id=payment_id).first() is not None


def _record_and_credit(db, user_id, payment_id, order_id, signature, amount_inr, credits_to_add):
    """
    Shared logic used by both /verify-payment and /webhook.
    Records the Razorpay transaction and adds credits via CreditService.
    """
    # 1. Record the Razorpay transaction for audit
    new_txn = RazorpayTransaction(
        razorpay_payment_id=payment_id,
        razorpay_order_id=order_id,
        razorpay_signature=signature,
        user_id=user_id,
        amount_inr=amount_inr,
        credits_added=credits_to_add
    )
    db.add(new_txn)
    db.flush()  # Flush to catch unique-constraint violations early

    # 2. Add credits via CreditService (consistent with existing credit system)
    new_balance = CreditService.add_credits(
        db=db,
        user_id=uuid.UUID(str(user_id)),
        amount=credits_to_add,
        transaction_type="purchase",
        description=f"Razorpay Recharge ₹{amount_inr} | Payment: {payment_id}"
    )

    # 3. Log activity
    log_user_activity(db, user_id, "RECHARGE", f"Added {credits_to_add} credits (₹{amount_inr})", {
        "payment_id": payment_id,
        "order_id": order_id,
        "amount_inr": amount_inr,
        "credits": credits_to_add
    })

    return new_balance


# ─── 1. CREATE ORDER ─────────────────────────────────────────────────────────
@razorpay_bp.route('/create-order', methods=['POST'])
@token_required
def create_order():
    """Creates a Razorpay order for the selected pricing tier."""
    data = request.json
    if not data or 'amount_inr' not in data:
        return jsonify({"success": False, "error": "amount_inr is required"}), 400

    amount = int(data['amount_inr'])
    if amount not in PRICING_TIERS:
        return jsonify({"success": False, "error": "Invalid pricing tier"}), 400

    try:
        order_data = {
            "amount": amount * 100,  # Convert to paise
            "currency": "INR",
            "receipt": f"rcpt_{str(request.user_id)[:8]}_{amount}",
            "notes": {
                "user_id": request.user_id,
                "credits": PRICING_TIERS[amount]
            }
        }
        order = get_razorpay_client().order.create(data=order_data)
        logger.info(f"Razorpay order created: {order['id']} for user {request.user_id}")

        return jsonify({
            "success": True,
            "data": {
                "order_id": order['id'],
                "amount": order['amount'],
                "currency": order['currency'],
                "key_id": get_razorpay_key_id()
            },
            "error": None
        })
    except Exception as e:
        logger.error(f"Error creating Razorpay order: {e}")
        return jsonify({"success": False, "error": "Failed to create payment order. Please try again."}), 500


# ─── 2. VERIFY PAYMENT (Synchronous — Primary) ──────────────────────────────
@razorpay_bp.route('/verify-payment', methods=['POST'])
@token_required
def verify_payment():
    """
    Verifies Razorpay payment signature and credits the user synchronously.
    This is the PRIMARY credit path — no webhook dependency.
    """
    data = request.json
    required_fields = ['razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature', 'credits']
    if not data or not all(f in data for f in required_fields):
        return jsonify({"success": False, "error": "Missing required payment fields"}), 400

    order_id = data['razorpay_order_id']
    payment_id = data['razorpay_payment_id']
    signature = data['razorpay_signature']
    credits_requested = int(data['credits'])

    # ── Step 1: Verify Razorpay Signature (HMAC-SHA256) ──
    try:
        generated_signature = hmac.new(
            get_razorpay_key_secret().encode('utf-8'),
            f"{order_id}|{payment_id}".encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(generated_signature, signature):
            logger.warning(f"Signature mismatch for payment {payment_id}")
            return jsonify({"success": False, "error": "Payment verification failed — invalid signature"}), 400
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return jsonify({"success": False, "error": "Signature verification error"}), 500

    # ── Step 2: Determine credits from the Razorpay order (server-side truth) ──
    try:
        order = get_razorpay_client().order.fetch(order_id)
        amount_inr = order['amount'] // 100
        credits_to_add = PRICING_TIERS.get(amount_inr, 0)

        if credits_to_add == 0:
            return jsonify({"success": False, "error": "Invalid order amount"}), 400
    except Exception as e:
        logger.error(f"Failed to fetch Razorpay order {order_id}: {e}")
        return jsonify({"success": False, "error": "Could not verify order details"}), 500

    # ── Step 3: Idempotency + Credit ──
    db = SessionLocal()
    try:
        if _is_payment_already_processed(db, payment_id):
            logger.info(f"Idempotency: Payment {payment_id} already processed.")
            user = db.query(User).filter(User.id == request.user_id).first()
            return jsonify({
                "success": True,
                "data": {
                    "message": "Payment already verified",
                    "credits": user.credits if user else 0
                },
                "error": None
            })

        new_balance = _record_and_credit(
            db, request.user_id, payment_id, order_id, signature, amount_inr, credits_to_add
        )

        logger.info(f"Payment {payment_id} verified. Added {credits_to_add} credits to user {request.user_id}. New balance: {new_balance}")

        return jsonify({
            "success": True,
            "data": {
                "message": "Payment verified and credits added",
                "credits_added": credits_to_add,
                "credits": new_balance
            },
            "error": None
        })

    except Exception as e:
        db.rollback()
        logger.error(f"Error processing payment verification: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to process payment. Contact support."}), 500
    finally:
        db.close()


# ─── 3. WEBHOOK (Asynchronous Fallback) ──────────────────────────────────────
@razorpay_bp.route('/webhook', methods=['POST'])
def webhook():
    """
    Handles Razorpay webhook events (payment.captured).
    Acts as a safety net — reuses the same idempotency logic.
    If /verify-payment already credited, this is a no-op.
    """
    webhook_secret = os.environ.get('RAZORPAY_WEBHOOK_SECRET', '')
    webhook_signature = request.headers.get('X-Razorpay-Signature')
    payload = request.data.decode('utf-8')

    if not webhook_signature or not webhook_secret:
        return jsonify({"status": "ignored", "reason": "No webhook secret configured"}), 200

    # Verify webhook signature
    try:
        get_razorpay_client().utility.verify_webhook_signature(payload, webhook_signature, webhook_secret)
    except Exception as e:
        logger.error(f"Webhook signature verification failed: {e}")
        return jsonify({"error": "Invalid signature"}), 400

    event = request.json
    if event.get('event') != 'payment.captured':
        return jsonify({"status": "ignored"}), 200

    payment_entity = event['payload']['payment']['entity']
    payment_id = payment_entity['id']
    order_id = payment_entity.get('order_id', '')
    amount_paid = payment_entity['amount'] // 100
    user_id = payment_entity.get('notes', {}).get('user_id')
    credits_to_add = PRICING_TIERS.get(amount_paid, 0)

    if not user_id or credits_to_add == 0:
        logger.error(f"Webhook: Invalid notes or tier. user_id={user_id}, amount={amount_paid}")
        return jsonify({"status": "ignored"}), 200

    db = SessionLocal()
    try:
        # Idempotency: skip if already processed by /verify-payment
        if _is_payment_already_processed(db, payment_id):
            logger.info(f"Webhook idempotency: Payment {payment_id} already processed.")
            return jsonify({"status": "already_processed"}), 200

        _record_and_credit(
            db, user_id, payment_id, order_id, webhook_signature, amount_paid, credits_to_add
        )
        logger.info(f"Webhook: Added {credits_to_add} credits for payment {payment_id}")
        return jsonify({"status": "ok"}), 200

    except Exception as e:
        db.rollback()
        logger.error(f"Webhook DB error: {e}", exc_info=True)
        return jsonify({"error": "Database error"}), 500
    finally:
        db.close()
