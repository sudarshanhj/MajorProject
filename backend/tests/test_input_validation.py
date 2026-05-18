import pytest
import io
import filetype
from werkzeug.datastructures import FileStorage

# We re-implement the exact logic here for unit testing purposes to isolate from Flask context.
def validate_uploaded_image(file_storage: FileStorage):
    header = file_storage.read(512)
    file_storage.seek(0)
    kind = filetype.guess(header)
    if kind is None or kind.mime not in ['image/png', 'image/jpeg', 'image/jpg', 'image/webp']:
        raise ValueError(f"Invalid file type. Found: {kind.extension if kind else 'Unknown'}. Only PNG/JPG/WEBP allowed.")

def create_mock_file(content: bytes, filename: str) -> FileStorage:
    return FileStorage(stream=io.BytesIO(content), filename=filename)

def test_validate_valid_png():
    # Valid PNG header signature
    png_signature = b"\x89PNG\r\n\x1a\n"
    # Pad to 512 bytes 
    padded = png_signature + b"\x00" * 504
    f = create_mock_file(padded, "test.png")
    
    # Should not raise exception
    validate_uploaded_image(f)

def test_validate_invalid_file_exe():
    exe_signature = b"MZ\x90\x00\x03\x00\x00\x00"
    padded = exe_signature + b"\x00" * 504
    f = create_mock_file(padded, "malware.exe")
    
    with pytest.raises(ValueError, match="Invalid file type"):
        validate_uploaded_image(f)

def test_validate_null_file():
    f = create_mock_file(b"\x00\x00\x00\x00", "empty.png")
    
    with pytest.raises(ValueError, match="Invalid file type"):
        validate_uploaded_image(f)
