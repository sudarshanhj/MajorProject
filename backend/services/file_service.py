import os
import uuid
from sqlalchemy.orm import Session
from models.file import File
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = os.path.join("data", "uploads")

class FileService:
    @staticmethod
    def save_file(db: Session, user_id: uuid.UUID, file_data: bytes, original_filename: str, file_type: str) -> File:
        """
        Saves file data to disk and records metadata in the database.
        file_type should be 'cover', 'secret', or 'stego'.
        """
        # Ensure directory exists (redundant but safe)
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Generate unique filename
        ext = os.path.splitext(original_filename)[1]
        unique_filename = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
        
        # Save to disk
        with open(file_path, "wb") as f:
            f.write(file_data)
            
        # Record in DB
        db_file = File(
            user_id=user_id,
            filename=original_filename,
            file_path=file_path,
            file_type=file_type,
            status="active"
        )
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        return db_file

    @staticmethod
    def create_record(db: Session, user_id: uuid.UUID, filename: str, file_type: str) -> File:
        """Records file metadata only (no disk save)."""
        db_file = File(
            user_id=user_id,
            filename=filename,
            file_path="VIRTUAL://",
            file_type=file_type,
            status="active"
        )
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        return db_file

    @staticmethod
    def get_user_files(db: Session, user_id: uuid.UUID):
        return db.query(File).filter(File.user_id == user_id).all()
