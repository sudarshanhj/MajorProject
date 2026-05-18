"""
Global pytest configuration for DeepStegAI backend tests.
Loads .env (including DATABASE_URL for Postgres) before importing any models or app.
"""
import sys
import os

# ── Fix 4: Load .env BEFORE importing app so DATABASE_URL=postgresql://... is picked up ──
from dotenv import load_dotenv
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(_env_path)

# Ensure the backend root is always on sys.path for all test files
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Override with test-specific env vars that should always win
os.environ.setdefault("TESTING", "True")
os.environ.setdefault("JWT_SECRET_KEY", "TEST_ONLY_SECRET_KEY_NOT_FOR_PRODUCTION")
# DATABASE_URL is sourced from .env (loaded above) — Postgres is used if configured there

import pytest

@pytest.fixture(scope="session")
def flask_app():
    """Provide the Flask app configured for testing."""
    from app import app
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    yield app

@pytest.fixture
def client(flask_app):
    """Provide a Flask test client for each test."""
    with flask_app.test_client() as c:
        yield c
