import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Index, JSON
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database.db import Base

analysis_verdict_enum = ENUM('CLEAN', 'SUSPICIOUS', 'DETECTED', name='analysis_verdict_enum', create_type=True)

class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    verdict = Column(analysis_verdict_enum, default="CLEAN", nullable=False)
    static_details = Column(JSONB, nullable=True)
    confidence_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True, nullable=False)

    # Relationships
    file = relationship("File", back_populates="analysis_results")

    def to_dict(self):
        # Standardized structure for static_details/analysis results
        details = self.static_details or {}
        
        # Ensure ai_score is always available as a float
        ai_score = self.confidence_score
        if ai_score is None:
            ai_score = details.get("ai_score") or details.get("ai_analysis", {}).get("score", 0.0)
            
        return {
            "id": str(self.id),
            "file_id": str(self.file_id),
            "verdict": str(self.verdict),
            "ai_score": float(ai_score) if ai_score is not None else 0.0,
            "details": details,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
