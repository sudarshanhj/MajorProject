from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional, Any

class AnalysisResultBase(BaseModel):
    confidence_score: Optional[float] = None
    result_data: Optional[Any] = None

class AnalysisResultCreate(AnalysisResultBase):
    file_id: UUID

class AnalysisResultResponse(AnalysisResultBase):
    id: UUID
    file_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
