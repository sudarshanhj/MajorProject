import pytest
import io
import json
import base64
from app import app
from database.db import SessionLocal, Base, engine
from models.user import User
from models.file import File

@pytest.fixture(scope="module")
def setup_database():
    """Setup a clean test database"""
    Base.metadata.create_all(bind=engine)
    yield
    # Rollback or drop tables not needed for persistent test db

@pytest.fixture
def client_app():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_stateless_embed_extract_flow(client_app, setup_database):
    """
    Validates complete stateless flow:
    Inject User -> DB -> Login -> Get Token -> 
    Upload Image & Data -> Embed in Memory -> Receive Stream ->
    Extract Data from Stream -> Compare
    """
    db = SessionLocal()
    
    # 1. Setup User
    test_email = "stateless_test@example.com"
    test_password = "StrongPassword123"
    
    existing_user = db.query(User).filter_by(email=test_email).first()
    if existing_user:
        db.delete(existing_user)
        db.commit()
    
    from utils.auth import hash_password
    user = User(
        email=test_email,
        password_hash=hash_password(test_password),
        credits=500,
        is_verified=True
    )
    db.add(user)
    db.commit()
    
    initial_file_count = db.query(File).filter(File.user_id == user.id).count()
    
    # 2. Login Flow to get JWT
    login_payload = {"email": test_email, "password": test_password}
    login_res = client_app.post('/api/auth/login', json=login_payload)
    assert login_res.status_code == 200
    token = json.loads(login_res.data)["data"]["access_token"]
    auth_header = {"Authorization": f"Bearer {token}"}
    
    # 3. Embed Flow (In-Memory Processing)
    import PIL.Image as Image
    img = Image.new('RGB', (200, 200), color='green')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    
    secret_data = b"STATELESS_INTEGRATION_TEST_SECRET_PAYLOAD_99999"
    
    embed_res = client_app.post(
        '/api/embed',
        headers=auth_header,
        data={
            'cover': (io.BytesIO(img_byte_arr.getvalue()), 'test_cover.png'),
            'secret': (io.BytesIO(secret_data), 'secret.txt'),
            'method': 'LSB',
            'password': 'StegoPassword123'
        },
        content_type='multipart/form-data'
    )
    assert embed_res.status_code == 200
    embed_data = json.loads(embed_res.data)
    
    # 4. Data Consistency Check (Atomic Credit Deduction + No DB File Storage)
    db.refresh(user)
    assert user.credits == 495 # 500 - 5
    
    # Crucial Stateless Check: Ensure absolutely no files were persisted to the database
    current_file_count = db.query(File).filter(File.user_id == user.id).count()
    assert current_file_count == initial_file_count, "Stateless violation: File was persisted to the database!"
    
    # 5. Extract Flow (In-Memory Response Validation)
    stego_bytes = base64.b64decode(embed_data["data"]["image_data"])
    recovery_token = embed_data["data"]["recovery_token"]
    
    extract_res = client_app.post(
        '/api/extract',
        headers=auth_header,
        data={
            'stego': (io.BytesIO(stego_bytes), 'stego_image.png'),
            'recovery_token': recovery_token
        },
        content_type='multipart/form-data'
    )
    assert extract_res.status_code == 200
    
    extracted_data = extract_res.data
    assert extracted_data == secret_data, "Data integrity lost across stateless stream boundary!"
    
    # Check credits dropped again
    db.refresh(user)
    assert user.credits == 493 # 495 - 2 (extract cost)

def test_atomic_credit_refund_on_failure(client_app, setup_database):
    """
    Validates that a failed API request automatically refunds the pre-deducted credits.
    """
    db = SessionLocal()
    
    test_email = "refund_test@example.com"
    existing_user = db.query(User).filter_by(email=test_email).first()
    if existing_user:
        db.delete(existing_user)
        db.commit()
    
    from utils.auth import hash_password
    user = User(
        email=test_email,
        password_hash=hash_password("Pass123"),
        credits=100,
        is_verified=True
    )
    db.add(user)
    db.commit()
    
    login_res = client_app.post('/api/auth/login', json={"email": test_email, "password": "Pass123"})
    token = json.loads(login_res.data)["data"]["access_token"]
    auth_header = {"Authorization": f"Bearer {token}"}
    
    # Intentionally trigger an error (missing secret file) in /embed which costs 5 credits
    # The @require_credits decorator should deduct 5, then refund 5 when the 400 error returns
    embed_res = client_app.post(
        '/api/embed',
        headers=auth_header,
        data={
            'method': 'LSB'
        },
        content_type='multipart/form-data'
    )
    
    assert embed_res.status_code == 400
    
    db.refresh(user)
    assert user.credits == 100, "Credit Rollback Failed! Credits were not refunded on 400 API Error."
    
    db.close()
