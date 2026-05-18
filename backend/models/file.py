import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Index
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.db import Base

# Define ENUMs for reused types
file_type_enum = ENUM('cover', 'secret', 'stego', name='file_type_enum', create_type=True)
file_status_enum = ENUM('active', 'expired', 'deleted', name='file_status_enum', create_type=True)

class File(Base):
    __tablename__ = "files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(file_type_enum, nullable=False)
    status = Column(file_status_enum, default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)

    __table_args__ = (
        Index('idx_files_user_created', 'user_id', 'created_at'),
    )

    # Relationships
    user = relationship("User", back_populates="files")
    analysis_results = relationship("AnalysisResult", back_populates="file", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "filename": self.filename,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
