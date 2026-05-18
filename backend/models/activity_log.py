import uuid
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from database.db import Base

class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    action = Column(String, nullable=False) # e.g., 'LOGIN', 'EMBED', 'EXTRACT', 'PAYMENT'
    details = Column(String, nullable=True) # Text description
    metadata_json = Column(JSON, nullable=True) # Any extra context
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "action": self.action,
            "details": self.details,
            "metadata_json": self.metadata_json,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
