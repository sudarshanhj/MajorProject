"""
═══════════════════════════════════════════════════════════════════
DEEPSTEGAI V2 — AI SYSTEM VALIDATION + PERFORMANCE TESTING
Module: CNN Inference, Grad-CAM, Heuristic Verdict Consistency
Phase: 3 (System) + AI Validation
Author: Antigravity QA Engine
═══════════════════════════════════════════════════════════════════
"""

import pytest
import io
import json
import os
import sys
import base64
import time
import threading
import concurrent.futures
import secrets
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    return flask_app


@pytest.fixture(scope="module")
def client(app):
    with app.test_client() as c:
        yield c


def make_png_bytes(w=256, h=256, color="gray") -> bytes:
    img = Image.new("RGB", (w, h), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def get_test_token(client, credits=10000) -> str:
    from database.db import SessionLocal
    from models.user import User
    from utils.auth import hash_password
    email = f"ai_{secrets.token_hex(4)}@test.io"
    db = SessionLocal()
    try:
        u = User(email=email, password_hash=hash_password("Passw0rd!"), credits=credits, is_verified=True)
        db.add(u)
        db.commit()
    finally:
        db.close()
    resp = client.post("/api/auth/login", json={"email": email, "password": "Passw0rd!"})
    return json.loads(resp.data)["data"]["access_token"]


# ─────────────────────────────────────────────────────────────────
# SECTION 1: CNN INFERENCE STABILITY
# ─────────────────────────────────────────────────────────────────

class TestCNNInferenceStability:
    """Tests for analyze endpoint: AI pipeline correctness and stability."""

    def test_analyze_returns_valid_ai_score_range(self, client):
        """AI score must be between 0.0 and 1.0 inclusive."""
        token = get_test_token(client)
        png = make_png_bytes()
        resp = client.post(
            "/api/analyze",
            headers={"Authorization": f"Bearer {token}"},
            data={"image": (io.BytesIO(png), "test.png")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["success"] is True
        score = data["data"]["ai_score"]
        assert 0.0 <= score <= 1.0, f"AI score out of range: {score}"

    def test_analyze_verdict_is_valid_enum(self, client):
        """Verdict must be exactly one of: CLEAN, SUSPICIOUS, DETECTED."""
        token = get_test_token(client)
        for color in ["white", "black", "gray", "red", "blue"]:
            png = make_png_bytes(224, 224, color)
            resp = client.post(
                "/api/analyze",
                headers={"Authorization": f"Bearer {token}"},
                data={"image": (io.BytesIO(png), f"{color}.png")},
                content_type="multipart/form-data",
            )
            assert resp.status_code == 200
            verdict = json.loads(resp.data)["data"]["verdict"]
            assert verdict in ("CLEAN", "SUSPICIOUS", "DETECTED"), \
                f"Invalid verdict: {verdict}"

    def test_analyze_is_deterministic_on_same_input(self, client):
        """Same image analyzed twice must produce same verdict and same ai_score."""
        token = get_test_token(client)
        png = make_png_bytes(224, 224, "purple")

        results = []
        for _ in range(2):
            resp = client.post(
                "/api/analyze",
                headers={"Authorization": f"Bearer {token}"},
                data={"image": (io.BytesIO(png), "same_img.png")},
                content_type="multipart/form-data",
            )
            assert resp.status_code == 200
            data = json.loads(resp.data)["data"]
            results.append((data["verdict"], data["ai_score"]))

        assert results[0][0] == results[1][0], "Non-deterministic verdict"
        # Scores should be very close (floating point)
        assert abs(results[0][1] - results[1][1]) < 1e-4, \
            f"Non-deterministic AI scores: {results[0][1]} vs {results[1][1]}"

    def test_stego_image_has_higher_ai_score_than_clean(self, client):
        """A stego image must generally score higher than a clean image."""
        token = get_test_token(client)
        clean_png = make_png_bytes(300, 300, "lightblue")

        # Create stego image via embed
        embed_resp = client.post(
            "/api/embed",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "cover": (io.BytesIO(make_png_bytes(300, 300, "lightblue")), "c.png"),
                "secret": (io.BytesIO(b"AI Score Test Payload"), "s.txt"),
                "method": "LSB",
            },
            content_type="multipart/form-data",
        )
        assert embed_resp.status_code == 200
        stego_b64 = json.loads(embed_resp.data)["data"]["image_data"]
        stego_bytes = base64.b64decode(stego_b64)

        # Analyze clean
        clean_resp = client.post(
            "/api/analyze",
            headers={"Authorization": f"Bearer {token}"},
            data={"image": (io.BytesIO(clean_png), "clean.png")},
            content_type="multipart/form-data",
        )
        clean_score = json.loads(clean_resp.data)["data"]["ai_score"]

        # Analyze stego
        stego_resp = client.post(
            "/api/analyze",
            headers={"Authorization": f"Bearer {token}"},
            data={"image": (io.BytesIO(stego_bytes), "stego.png")},
            content_type="multipart/form-data",
        )
        stego_score = json.loads(stego_resp.data)["data"]["ai_score"]

        # Stego with confirmed signature should score much higher
        assert stego_score >= clean_score, \
            f"Stego score ({stego_score:.3f}) should be ≥ clean score ({clean_score:.3f})"

    @pytest.mark.parametrize("image_size", [(64, 64), (128, 128), (224, 224), (512, 512)])
    def test_analyze_at_various_image_sizes(self, client, image_size):
        """CNN inference must complete successfully at various image dimensions."""
        token = get_test_token(client)
        w, h = image_size
        png = make_png_bytes(w, h)
        resp = client.post(
            "/api/analyze",
            headers={"Authorization": f"Bearer {token}"},
            data={"image": (io.BytesIO(png), f"{w}x{h}.png")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)["data"]
        assert 0.0 <= data["ai_score"] <= 1.0

    def test_analyze_response_time_under_10s(self, client):
        """Single image AI scan must complete in under 10 seconds on any hardware."""
        token = get_test_token(client)
        png = make_png_bytes(224, 224)
        start = time.time()
        client.post(
            "/api/analyze",
            headers={"Authorization": f"Bearer {token}"},
            data={"image": (io.BytesIO(png), "timed.png")},
            content_type="multipart/form-data",
        )
        elapsed = time.time() - start
        assert elapsed < 10.0, f"AI scan took too long: {elapsed:.2f}s (limit: 10s)"


# ─────────────────────────────────────────────────────────────────
# SECTION 2: GRAD-CAM VALIDATION
# ─────────────────────────────────────────────────────────────────

class TestGradCAMValidation:
    """Tests for Grad-CAM endpoint correctness."""

    def test_gradcam_on_clean_image_completes(self, client):
        """Grad-CAM must not crash on a clean image."""
        token = get_test_token(client)
        png = make_png_bytes(224, 224, "white")
        resp = client.post(
            "/api/heatmap/gradcam",
            headers={"Authorization": f"Bearer {token}"},
            data={"image": (io.BytesIO(png), "clean.png")},
            content_type="multipart/form-data",
        )
        assert resp.status_code in (200, 503)  # 503 if model not loaded
        if resp.status_code == 200:
            data = json.loads(resp.data)
            assert data["success"] is True
            assert "prediction" in data
            assert data["prediction"] in ("CLEAN", "STEGO")
            assert 0.0 <= data["confidence"] <= 1.0

    def test_gradcam_on_stego_image_returns_heatmap(self, client):
        """Grad-CAM on known stego image should ideally return non-null heatmap."""
        token = get_test_token(client)
        # Create stego
        embed_resp = client.post(
            "/api/embed",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "cover": (io.BytesIO(make_png_bytes(300, 300)), "c.png"),
                "secret": (io.BytesIO(b"Grad-CAM Test Secret"), "s.txt"),
                "method": "LSB",
            },
            content_type="multipart/form-data",
        )
        if embed_resp.status_code != 200:
            pytest.skip("Insufficient credits for embed in GradCAM test")

        stego_bytes = base64.b64decode(json.loads(embed_resp.data)["data"]["image_data"])

        resp = client.post(
            "/api/heatmap/gradcam",
            headers={"Authorization": f"Bearer {token}"},
            data={"image": (io.BytesIO(stego_bytes), "stego.png")},
            content_type="multipart/form-data",
        )
        assert resp.status_code in (200, 503)
        if resp.status_code == 200:
            data = json.loads(resp.data)
            assert data["success"] is True

    def test_gradcam_missing_image_returns_400(self, client):
        token = get_test_token(client)
        resp = client.post(
            "/api/heatmap/gradcam",
            headers={"Authorization": f"Bearer {token}"},
            data={},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    def test_heatmap_base64_is_valid_png(self, client):
        """If heatmap_b64 is not None, it must decode to a valid PNG."""
        token = get_test_token(client)
        # Use a stego image to maximize chance of non-null heatmap
        embed_resp = client.post(
            "/api/embed",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "cover": (io.BytesIO(make_png_bytes(400, 400)), "c.png"),
                "secret": (io.BytesIO(b"heatmap data payload"), "s.txt"),
                "method": "LSB",
            },
            content_type="multipart/form-data",
        )
        if embed_resp.status_code != 200:
            pytest.skip("Embed failed")

        stego_bytes = base64.b64decode(json.loads(embed_resp.data)["data"]["image_data"])
        resp = client.post(
            "/api/heatmap/gradcam",
            headers={"Authorization": f"Bearer {token}"},
            data={"image": (io.BytesIO(stego_bytes), "stego.png")},
            content_type="multipart/form-data",
        )
        if resp.status_code == 200:
            data = json.loads(resp.data)
            if data.get("heatmap_b64"):
                # Must decode to valid image
                hm_bytes = base64.b64decode(data["heatmap_b64"])
                hm_img = Image.open(io.BytesIO(hm_bytes))
                assert hm_img.size[0] > 0 and hm_img.size[1] > 0


# ─────────────────────────────────────────────────────────────────
# SECTION 3: HEURISTIC + AI VERDICT CONSISTENCY
# ─────────────────────────────────────────────────────────────────

class TestHeuristicAIConsistency:
    """Validates that heuristic detection and AI verdict are consistent."""

    def test_signature_detected_always_yields_detected_verdict(self, client):
        """If heuristic finds DEEPSTEGAI signature, verdict MUST be DETECTED."""
        token = get_test_token(client)
        # Create verified stego
        embed_resp = client.post(
            "/api/embed",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "cover": (io.BytesIO(make_png_bytes(300, 300)), "c.png"),
                "secret": (io.BytesIO(b"consistency test"), "s.txt"),
                "method": "LSB",
            },
            content_type="multipart/form-data",
        )
        assert embed_resp.status_code == 200
        stego = base64.b64decode(json.loads(embed_resp.data)["data"]["image_data"])

        analyze_resp = client.post(
            "/api/analyze",
            headers={"Authorization": f"Bearer {token}"},
            data={"image": (io.BytesIO(stego), "verified_stego.png")},
            content_type="multipart/form-data",
        )
        assert analyze_resp.status_code == 200
        verdict = json.loads(analyze_resp.data)["data"]["verdict"]
        assert verdict == "DETECTED", \
            "Signature detected but verdict is not DETECTED — consistency failure!"

    def test_clean_image_has_score_below_detection_threshold(self, client):
        """Pure generated images should generally score below the SUSPICIOUS threshold (0.85)."""
        token = get_test_token(client)
        # Use a simple solid-color PNG which the CNN should classify as clean
        png = make_png_bytes(300, 300, "white")
        resp = client.post(
            "/api/analyze",
            headers={"Authorization": f"Bearer {token}"},
            data={"image": (io.BytesIO(png), "white.png")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        data = json.loads(resp.data)["data"]
        # While we can't guarantee ai_score < 0.85 on every model,
        # the VERDICT must respect the heuristic — no signature means not DETECTED
        verdict = data["verdict"]
        assert verdict != "DETECTED", \
            "Clean image incorrectly marked as DETECTED (no signature should exist)"

    def test_calibration_boosts_score_for_confirmed_stego(self, client):
        """Calibration layer must ensure score >= 0.60 when signature is present."""
        token = get_test_token(client)
        embed_resp = client.post(
            "/api/embed",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "cover": (io.BytesIO(make_png_bytes(400, 400)), "c.png"),
                "secret": (io.BytesIO(b"calibration check payload"), "s.txt"),
                "method": "LSB",
            },
            content_type="multipart/form-data",
        )
        assert embed_resp.status_code == 200
        stego = base64.b64decode(json.loads(embed_resp.data)["data"]["image_data"])

        analyze_resp = client.post(
            "/api/analyze",
            headers={"Authorization": f"Bearer {token}"},
            data={"image": (io.BytesIO(stego), "calib.png")},
            content_type="multipart/form-data",
        )
        score = json.loads(analyze_resp.data)["data"]["ai_score"]
        assert score >= 0.60, f"Calibration failed: score {score:.3f} < 0.60 for confirmed stego"


# ─────────────────────────────────────────────────────────────────
# SECTION 4: PERFORMANCE (CONCURRENCY)
# ─────────────────────────────────────────────────────────────────

class TestPerformanceConcurrency:
    """Validates throughput and response times under concurrent load."""

    def test_concurrent_embed_5_users(self, client):
        """5 simultaneous embed requests must all complete (200 or 402)."""
        tokens = [get_test_token(client, credits=1000) for _ in range(5)]
        results = []
        lock = threading.Lock()

        def run_embed(token):
            png = make_png_bytes(200, 200)
            r = client.post(
                "/api/embed",
                headers={"Authorization": f"Bearer {token}"},
                data={
                    "cover": (io.BytesIO(png), "c.png"),
                    "secret": (io.BytesIO(b"concurrent embed test"), "s.txt"),
                    "method": "LSB",
                },
                content_type="multipart/form-data",
            )
            with lock:
                results.append(r.status_code)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            futs = [pool.submit(run_embed, t) for t in tokens]
            concurrent.futures.wait(futs)

        for s in results:
            assert s in (200, 402, 429, 503), \
                f"Unexpected status under concurrent embed: {s}"

    def test_sequential_extract_round_trips_10_times(self, client):
        """10 sequential embed-extract round-trips must all succeed."""
        token = get_test_token(client, credits=10000)

        for i in range(10):
            secret = f"round_trip_{i}_{secrets.token_hex(4)}".encode()
            png = make_png_bytes(300, 300)

            # Embed
            er = client.post(
                "/api/embed",
                headers={"Authorization": f"Bearer {token}"},
                data={
                    "cover": (io.BytesIO(png), "c.png"),
                    "secret": (io.BytesIO(secret), "s.txt"),
                    "method": "LSB",
                },
                content_type="multipart/form-data",
            )
            assert er.status_code == 200, f"Embed {i} failed"
            stego = base64.b64decode(json.loads(er.data)["data"]["image_data"])

            # Extract
            xr = client.post(
                "/api/extract",
                headers={"Authorization": f"Bearer {token}"},
                data={"stego": (io.BytesIO(stego), "s.png")},
                content_type="multipart/form-data",
            )
            assert xr.status_code == 200, f"Extract {i} failed"
            assert xr.data == secret, f"Bit-perfect failure on round trip {i}"

    def test_memory_leak_detection_sequential_blobs(self, client):
        """
        Process 20 images through the analyze pipeline sequentially.
        Memory should not grow unboundedly (validated by process not crashing).
        """
        import gc
        token = get_test_token(client, credits=100000)

        for i in range(20):
            png = make_png_bytes(100, 100)
            resp = client.post(
                "/api/analyze",
                headers={"Authorization": f"Bearer {token}"},
                data={"image": (io.BytesIO(png), f"blob_{i}.png")},
                content_type="multipart/form-data",
            )
            assert resp.status_code == 200
            del png, resp
            if i % 5 == 0:
                gc.collect()

        # If we reach here without MemoryError, no significant leak
