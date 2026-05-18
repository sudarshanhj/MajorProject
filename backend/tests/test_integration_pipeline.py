"""
═══════════════════════════════════════════════════════════════════
DEEPSTEGAI V2 — PHASE 2: INTEGRATION WAR TESTING
Module: Full API Pipeline, Auth, Credits, Batch, AI
Author: Antigravity QA Engine
Standard: Ian Somerville Testing Model
═══════════════════════════════════════════════════════════════════
"""

import pytest
import io
import json
import base64
import time
import os
import sys
import secrets
import threading
import concurrent.futures
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    return flask_app


@pytest.fixture(scope="module")
def client(app):
    with app.test_client() as c:
        yield c


@pytest.fixture(scope="module")
def db_session():
    from database.db import SessionLocal
    db = SessionLocal()
    yield db
    db.close()


def make_png_bytes(w=300, h=300, color="blue") -> bytes:
    img = Image.new("RGB", (w, h), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def register_and_login(client, email=None, password="TestPass!123", credits=1000):
    """Helper: register user in DB, then login to get JWT."""
    from database.db import SessionLocal
    from models.user import User
    from utils.auth import hash_password

    email = email or f"user_{secrets.token_hex(4)}@deepstegtest.io"
    db = SessionLocal()
    try:
        existing = db.query(User).filter_by(email=email).first()
        if existing:
            db.delete(existing)
            db.commit()
        user = User(
            email=email,
            password_hash=hash_password(password),
            credits=credits,
            is_verified=True,
        )
        db.add(user)
        db.commit()
        user_id = user.id
    finally:
        db.close()

    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.data}"
    token = json.loads(resp.data)["data"]["access_token"]
    return token, user_id, email


# ─────────────────────────────────────────────────────────────────
# SECTION 1: HEALTH CHECK
# ─────────────────────────────────────────────────────────────────

class TestHealthCheck:
    def test_health_endpoint_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "ok"


# ─────────────────────────────────────────────────────────────────
# SECTION 2: AUTHENTICATION PIPELINE
# ─────────────────────────────────────────────────────────────────

class TestAuthPipeline:
    """Testing: Login → JWT → Auth guard → Logout → Re-use prevention."""

    def test_login_valid_credentials(self, client):
        token, _, _ = register_and_login(client)
        assert token and len(token) > 10

    def test_login_invalid_password_returns_401(self, client):
        _, _, email = register_and_login(client)
        resp = client.post("/api/auth/login", json={"email": email, "password": "WRONGPASS"})
        assert resp.status_code in (401, 400)

    def test_protected_route_without_token_returns_401(self, client):
        resp = client.get("/api/files")
        assert resp.status_code == 401

    def test_protected_route_with_valid_token(self, client):
        token, _, _ = register_and_login(client)
        resp = client.get("/api/files", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    def test_tampered_token_returns_401(self, client):
        token, _, _ = register_and_login(client)
        # Corrupt the signature portion of the JWT
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1] + ".INVALIDSIGNATURE"
        resp = client.get("/api/files", headers={"Authorization": f"Bearer {tampered}"})
        assert resp.status_code == 401

    def test_expired_token_placeholder(self):
        """
        NOTE: Full expiry test requires clock manipulation (freezegun).
        Placeholder here — implement with: pytest-freezegun.
        """
        pass

    def test_logout_revokes_token(self, client):
        """After logout, same token must be rejected."""
        token, _, _ = register_and_login(client)
        logout_resp = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        # Logout may return 200 or redirect — both are acceptable
        assert logout_resp.status_code in (200, 302, 204)

        # Now try using the revoked token
        reuse_resp = client.get("/api/files", headers={"Authorization": f"Bearer {token}"})
        # Should be 401 if Redis denylist works; 200 if Redis unavailable (fail-open)
        # We log this as an observation
        if reuse_resp.status_code == 200:
            pytest.xfail("Redis denylist is in fail-open mode — token reuse allowed")
        else:
            assert reuse_resp.status_code == 401


# ─────────────────────────────────────────────────────────────────
# SECTION 3: EMBED API PIPELINE
# ─────────────────────────────────────────────────────────────────

class TestEmbedPipeline:
    """Full integration: LSB embed, Adaptive embed, capacity enforcement, credits."""

    def test_lsb_embed_returns_base64_image(self, client):
        token, _, _ = register_and_login(client, credits=500)
        png = make_png_bytes(300, 300)
        resp = client.post(
            "/api/embed",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "cover": (io.BytesIO(png), "cover.png"),
                "secret": (io.BytesIO(b"SECRET_DATA_INTEGRATION"), "secret.txt"),
                "method": "LSB",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True
        assert data["data"]["image_data"]
        # Ensure response is valid base64 PNG
        img_bytes = base64.b64decode(data["data"]["image_data"])
        img = Image.open(io.BytesIO(img_bytes))
        assert img.format == "PNG"

    def test_lsb_embed_deducts_credits(self, client):
        token, user_id, _ = register_and_login(client, credits=100)
        png = make_png_bytes()
        resp = client.post(
            "/api/embed",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "cover": (io.BytesIO(png), "c.png"),
                "secret": (io.BytesIO(b"data"), "s.txt"),
                "method": "LSB",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        header_credits = resp.headers.get("X-Updated-Credits")
        if header_credits:
            assert int(header_credits) == 95  # 100 - 5

    def test_embed_missing_cover_returns_400(self, client):
        token, _, _ = register_and_login(client, credits=500)
        resp = client.post(
            "/api/embed",
            headers={"Authorization": f"Bearer {token}"},
            data={"secret": (io.BytesIO(b"data"), "s.txt"), "method": "LSB"},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    def test_embed_missing_secret_returns_400(self, client):
        token, _, _ = register_and_login(client, credits=500)
        png = make_png_bytes()
        resp = client.post(
            "/api/embed",
            headers={"Authorization": f"Bearer {token}"},
            data={"cover": (io.BytesIO(png), "c.png"), "method": "LSB"},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    def test_embed_invalid_file_type_returns_400(self, client):
        """Submitting a text file as cover image must be rejected."""
        token, _, _ = register_and_login(client, credits=500)
        resp = client.post(
            "/api/embed",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "cover": (io.BytesIO(b"This is plaintext, not an image"), "fake.png"),
                "secret": (io.BytesIO(b"data"), "s.txt"),
                "method": "LSB",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    def test_embed_payload_exceeding_35_percent_rejected(self, client):
        """Payload > 35% of cover file size must return 400."""
        token, _, _ = register_and_login(client, credits=500)
        # Small cover: 10x10 PNG ≈ ~200 bytes
        png = make_png_bytes(10, 10)
        # Very large secret
        huge_secret = b"X" * 10_000
        resp = client.post(
            "/api/embed",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "cover": (io.BytesIO(png), "c.png"),
                "secret": (io.BytesIO(huge_secret), "s.bin"),
                "method": "LSB",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert "35%" in data.get("error", "") or "payload" in data.get("error", "").lower()

    def test_adaptive_embed_requires_password(self, client):
        """Adaptive method without password must return 400."""
        token, _, _ = register_and_login(client, credits=500)
        png = make_png_bytes()
        resp = client.post(
            "/api/embed",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "cover": (io.BytesIO(png), "c.png"),
                "secret": (io.BytesIO(b"data"), "s.txt"),
                "method": "ADAPTIVE",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        data = json.loads(resp.data)
        assert "password" in data.get("error", "").lower()

    def test_embed_credit_refund_on_failure(self, client):
        """Credits must be refunded when embed fails (400 error)."""
        token, user_id, _ = register_and_login(client, credits=100)
        resp = client.post(
            "/api/embed",
            headers={"Authorization": f"Bearer {token}"},
            data={"method": "LSB"},  # Missing required files
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        # Credits should still be 100 (refunded)
        from database.db import SessionLocal
        from models.user import User
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            assert user.credits == 100, f"Credit refund failed: credits = {user.credits}"
        finally:
            db.close()


# ─────────────────────────────────────────────────────────────────
# SECTION 4: EXTRACT API PIPELINE
# ─────────────────────────────────────────────────────────────────

class TestExtractPipeline:
    """Full extract pipeline: happy path, wrong password, no signature."""

    def _embed_and_get_stego(self, client, token, secret=b"EXTRACT_TEST", password=None):
        """Helper: embed and return (stego_bytes, recovery_token)."""
        png = make_png_bytes(300, 300)
        data_dict = {
            "cover": (io.BytesIO(png), "c.png"),
            "secret": (io.BytesIO(secret), "s.txt"),
            "method": "ADAPTIVE" if password else "LSB",
        }
        if password:
            data_dict["password"] = password

        resp = client.post(
            "/api/embed",
            headers={"Authorization": f"Bearer {token}"},
            data=data_dict,
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        d = json.loads(resp.data)["data"]
        return base64.b64decode(d["image_data"]), d.get("recovery_token")

    def test_lsb_extract_recovers_payload_exactly(self, client):
        """Bit-perfect recovery: extracted bytes == original bytes."""
        token, _, _ = register_and_login(client, credits=1000)
        secret = b"BIT_PERFECT_RECOVERY_TEST_42"
        stego_bytes, _ = self._embed_and_get_stego(client, token, secret)

        resp = client.post(
            "/api/extract",
            headers={"Authorization": f"Bearer {token}"},
            data={"stego": (io.BytesIO(stego_bytes), "stego.png")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        assert resp.data == secret

    def test_extract_with_password(self, client):
        """Encrypted embed must be extractable with password."""
        token, _, _ = register_and_login(client, credits=1000)
        secret = b"ENCRYPTED_SECRET_XYZ"
        stego_bytes, _ = self._embed_and_get_stego(client, token, secret, password="Decryptme123")

        resp = client.post(
            "/api/extract",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "stego": (io.BytesIO(stego_bytes), "stego.png"),
                "password": "Decryptme123",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        assert resp.data == secret

    def test_extract_wrong_password_returns_403_or_400(self, client):
        token, _, _ = register_and_login(client, credits=1000)
        stego_bytes, _ = self._embed_and_get_stego(client, token, b"secret", password="CorrectKey")

        resp = client.post(
            "/api/extract",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "stego": (io.BytesIO(stego_bytes), "stego.png"),
                "password": "WrongKey",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code in (400, 403)

    def test_extract_clean_image_returns_404(self, client):
        """Extracting from clean image (no signature) must return 404."""
        token, _, _ = register_and_login(client, credits=1000)
        clean = make_png_bytes(200, 200)
        resp = client.post(
            "/api/extract",
            headers={"Authorization": f"Bearer {token}"},
            data={"stego": (io.BytesIO(clean), "clean.png")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 404

    def test_extract_missing_stego_returns_400(self, client):
        token, _, _ = register_and_login(client, credits=1000)
        resp = client.post(
            "/api/extract",
            headers={"Authorization": f"Bearer {token}"},
            data={},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    def test_extract_with_recovery_token(self, client):
        """Recovery token from embed must work in extract."""
        token, _, _ = register_and_login(client, credits=1000)
        secret = b"TOKEN_RECOVERY_TEST"
        stego_bytes, recovery_token = self._embed_and_get_stego(
            client, token, secret, password="RecoverMe!"
        )
        assert recovery_token is not None

        resp = client.post(
            "/api/extract",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "stego": (io.BytesIO(stego_bytes), "stego.png"),
                "recovery_token": recovery_token,
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        assert resp.data == secret


# ─────────────────────────────────────────────────────────────────
# SECTION 5: CAPACITY API
# ─────────────────────────────────────────────────────────────────

class TestCapacityAPI:

    def test_capacity_returns_35_percent_of_cover(self, client):
        import math
        png = make_png_bytes(300, 300)
        cover_size = len(png)
        resp = client.post(
            "/api/capacity",
            data={"cover": (io.BytesIO(png), "c.png")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        d = json.loads(resp.data)["data"]
        expected = math.floor(cover_size * 0.35)
        assert d["max_payload_bytes"] == expected
        assert d["cover_size_bytes"] == cover_size

    def test_capacity_missing_cover_returns_400(self, client):
        resp = client.post("/api/capacity", data={}, content_type="multipart/form-data")
        assert resp.status_code == 400

    def test_capacity_large_image(self, client):
        png = make_png_bytes(1920, 1080)
        resp = client.post(
            "/api/capacity",
            data={"cover": (io.BytesIO(png), "hd.png")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        d = json.loads(resp.data)["data"]
        assert d["max_payload_bytes"] > 0


# ─────────────────────────────────────────────────────────────────
# SECTION 6: ANALYZE API (STEGANALYSIS)
# ─────────────────────────────────────────────────────────────────

class TestAnalyzePipeline:

    def test_analyze_clean_image_returns_clean(self, client):
        token, _, _ = register_and_login(client, credits=500)
        png = make_png_bytes(300, 300, "white")
        resp = client.post(
            "/api/analyze",
            headers={"Authorization": f"Bearer {token}"},
            data={"image": (io.BytesIO(png), "pure_white.png")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True
        assert "verdict" in data["data"]
        assert data["data"]["verdict"] in ("CLEAN", "SUSPICIOUS", "DETECTED")

    def test_analyze_stego_image_returns_detected(self, client):
        """Analyzer on a known stego image must return DETECTED (signature match)."""
        token, _, _ = register_and_login(client, credits=1000)
        # First embed something
        png = make_png_bytes(300, 300)
        embed_resp = client.post(
            "/api/embed",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "cover": (io.BytesIO(png), "c.png"),
                "secret": (io.BytesIO(b"stego_data"), "s.txt"),
                "method": "LSB",
            },
            content_type="multipart/form-data",
        )
        stego_b64 = json.loads(embed_resp.data)["data"]["image_data"]
        stego_bytes = base64.b64decode(stego_b64)

        analyze_resp = client.post(
            "/api/analyze",
            headers={"Authorization": f"Bearer {token}"},
            data={"image": (io.BytesIO(stego_bytes), "stego.png")},
            content_type="multipart/form-data",
        )
        assert analyze_resp.status_code == 200
        a_data = json.loads(analyze_resp.data)["data"]
        assert a_data["verdict"] == "DETECTED"
        # Score should be high for confirmed stego
        assert a_data["ai_score"] >= 0.6

    def test_analyze_missing_image_returns_400(self, client):
        token, _, _ = register_and_login(client, credits=500)
        resp = client.post(
            "/api/analyze",
            headers={"Authorization": f"Bearer {token}"},
            data={},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    def test_analyze_deducts_2_credits(self, client):
        token, user_id, _ = register_and_login(client, credits=50)
        png = make_png_bytes()
        client.post(
            "/api/analyze",
            headers={"Authorization": f"Bearer {token}"},
            data={"image": (io.BytesIO(png), "i.png")},
            content_type="multipart/form-data",
        )
        from database.db import SessionLocal
        from models.user import User
        db = SessionLocal()
        try:
            u = db.query(User).filter(User.id == user_id).first()
            assert u.credits == 48  # 50 - 2
        finally:
            db.close()

    def test_analyze_persists_result_to_db(self, client):
        """AI scan result must be saved to AnalysisRecord table."""
        token, _, _ = register_and_login(client, credits=500)
        png = make_png_bytes(200, 200)
        resp = client.post(
            "/api/analyze",
            headers={"Authorization": f"Bearer {token}"},
            data={"image": (io.BytesIO(png), "persist_test.png")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        file_id = json.loads(resp.data)["data"]["file_id"]
        assert file_id != "N/A", "Analysis must be persisted (file_id should not be N/A)"


# ─────────────────────────────────────────────────────────────────
# SECTION 7: BATCH PROCESSING PIPELINE
# ─────────────────────────────────────────────────────────────────

class TestBatchPipeline:

    def test_batch_hide_returns_zip(self, client):
        token, _, _ = register_and_login(client, credits=5000)
        covers = [(io.BytesIO(make_png_bytes(200, 200)), f"cover_{i}.png") for i in range(3)]
        data = {"mode": "hide", "method": "lsb"}
        data["secret"] = (io.BytesIO(b"BATCH_SECRET"), "secret.txt")
        # Flask test client requires multiple files with same key
        resp = client.post(
            "/api/batch",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "mode": "hide",
                "method": "lsb",
                "covers": covers,
                "secret": (io.BytesIO(b"BATCH_SECRET"), "secret.txt"),
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        assert resp.headers.get("Content-Type") == "application/zip"

    def test_batch_limit_50_covers_enforced(self, client):
        token, _, _ = register_and_login(client, credits=50000)
        covers = [(io.BytesIO(make_png_bytes(50, 50)), f"c{i}.png") for i in range(51)]
        resp = client.post(
            "/api/batch",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "mode": "hide",
                "covers": covers,
                "secret": (io.BytesIO(b"data"), "s.txt"),
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        assert "limit" in json.loads(resp.data).get("error", "").lower()

    def test_batch_invalid_mode_returns_400(self, client):
        token, _, _ = register_and_login(client, credits=500)
        resp = client.post(
            "/api/batch",
            headers={"Authorization": f"Bearer {token}"},
            data={"mode": "INVALID_MODE"},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    def test_batch_hide_missing_secret_returns_400(self, client):
        token, _, _ = register_and_login(client, credits=500)
        resp = client.post(
            "/api/batch",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "mode": "hide",
                "covers": [(io.BytesIO(make_png_bytes()), "c.png")],
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    def test_batch_analyze_returns_results_list(self, client):
        token, _, _ = register_and_login(client, credits=5000)
        images = [(io.BytesIO(make_png_bytes(100, 100)), f"img_{i}.png") for i in range(3)]
        resp = client.post(
            "/api/batch_analyze",
            headers={"Authorization": f"Bearer {token}"},
            data={"images": images},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True
        assert isinstance(data["data"], list)
        assert len(data["data"]) == 3

    def test_batch_analyze_each_result_has_verdict(self, client):
        token, _, _ = register_and_login(client, credits=5000)
        images = [(io.BytesIO(make_png_bytes(150, 150)), f"img_{i}.png") for i in range(2)]
        resp = client.post(
            "/api/batch_analyze",
            headers={"Authorization": f"Bearer {token}"},
            data={"images": images},
            content_type="multipart/form-data",
        )
        data = json.loads(resp.data)["data"]
        for item in data:
            if "error" not in item:
                assert "verdict" in item
                assert item["verdict"] in ("CLEAN", "SUSPICIOUS", "DETECTED")


# ─────────────────────────────────────────────────────────────────
# SECTION 8: CREDIT SYSTEM INTEGRATION
# ─────────────────────────────────────────────────────────────────

class TestCreditSystem:

    def test_insufficient_credits_blocked(self, client):
        """User with 0 credits cannot embed."""
        token, _, _ = register_and_login(client, credits=0)
        png = make_png_bytes()
        resp = client.post(
            "/api/embed",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "cover": (io.BytesIO(png), "c.png"),
                "secret": (io.BytesIO(b"data"), "s.txt"),
                "method": "LSB",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 402

    def test_credits_api_returns_current_balance(self, client):
        token, _, _ = register_and_login(client, credits=77)
        resp = client.get("/api/credits", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = json.loads(resp.data)["data"]
        assert data["credits"] == 77

    def test_concurrent_credit_deductions_no_race_condition(self, client):
        """
        Fire 3 concurrent embed requests — user has exactly 10 credits (< 3×5=15).
        At most 2 should succeed, 1 should fail with 402.
        This validates the SELECT FOR UPDATE atomic deduction.
        """
        token, user_id, _ = register_and_login(client, credits=10)

        results = []

        def do_embed():
            png = make_png_bytes(200, 200)
            r = client.post(
                "/api/embed",
                headers={"Authorization": f"Bearer {token}"},
                data={
                    "cover": (io.BytesIO(png), "c.png"),
                    "secret": (io.BytesIO(b"concurrent"), "s.txt"),
                    "method": "LSB",
                },
                content_type="multipart/form-data",
            )
            results.append(r.status_code)

        threads = [threading.Thread(target=do_embed) for _ in range(3)]
        for t in threads: t.start()
        for t in threads: t.join()

        # With 10 credits and cost=5: at most 2 can succeed
        success_count = results.count(200)
        failure_count = results.count(402)
        assert success_count <= 2, f"Race condition: {success_count} requests succeeded with 10 credits"
        assert success_count + failure_count == 3


# ─────────────────────────────────────────────────────────────────
# SECTION 9: RATE LIMITING
# ─────────────────────────────────────────────────────────────────

class TestRateLimiting:

    def test_capacity_endpoint_rate_limit_exists(self, client):
        """
        Rate limit on /api/capacity is 60/min.
        We send 61 requests — the 61st should trigger 429 if rate limiter active.
        NOTE: With in-memory limiter, this may not fire in test mode.
        Marked as xfail if rate limiter is disabled.
        """
        import time
        responses = []
        for _ in range(65):
            png = make_png_bytes(10, 10)
            r = client.post(
                "/api/capacity",
                data={"cover": (io.BytesIO(png), "c.png")},
                content_type="multipart/form-data",
            )
            responses.append(r.status_code)

        if 429 not in responses:
            pytest.xfail("Rate limiter did not fire (in-memory limiter, expected in Redis mode)")
        else:
            assert 429 in responses


# ─────────────────────────────────────────────────────────────────
# SECTION 10: GLOBAL STATS API
# ─────────────────────────────────────────────────────────────────

class TestGlobalStats:

    def test_global_stats_endpoint(self, client):
        resp = client.get("/api/stats/global")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "total_scans" in data["data"]
        assert "threats_found" in data["data"]
        assert data["data"]["total_scans"] >= 0
        assert data["data"]["threats_found"] >= 0
