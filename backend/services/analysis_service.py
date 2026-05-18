from sqlalchemy.orm import Session
from models.analysis_result import AnalysisResult
import uuid
from typing import Any, Dict, Optional

import logging

logger = logging.getLogger("DeepStegAI")

class AnalysisService:
    @staticmethod
    def save_analysis(db: Session, file_id: uuid.UUID, verdict: str, confidence: float, static_details: Optional[Dict[str, Any]] = None) -> AnalysisResult:
        """
        Records analysis results in the database.
        verdict should be 'CLEAN', 'SUSPICIOUS', or 'DETECTED'.
        """
        try:
            logger.info(f"Saving analysis result for file {file_id}: verdict={verdict}, score={confidence}")
            
            result = AnalysisResult(
                file_id=file_id,
                verdict=verdict,
                confidence_score=confidence,
                static_details=static_details
            )
            db.add(result)
            db.commit()
            db.refresh(result)
            
            logger.info(f"Successfully saved analysis result {result.id}")
            return result
        except Exception as e:
            logger.error(f"Failed to save analysis result: {str(e)}")
            db.rollback()
            raise

    @staticmethod
    def get_analysis_by_file(db: Session, file_id: uuid.UUID) -> Optional[AnalysisResult]:
        return db.query(AnalysisResult).filter(AnalysisResult.file_id == file_id).first()

    @staticmethod
    def get_user_analyses(db: Session, user_id: uuid.UUID):
        from models.file import File
        # Explicit join for cross-database engine compatibility
        return db.query(AnalysisResult).join(File, AnalysisResult.file_id == File.id).filter(File.user_id == user_id).order_by(AnalysisResult.created_at.desc()).all()
