from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional

class FileBase(BaseModel):
    filename: str
    file_type: str
    status: str = "pending"

class FileCreate(FileBase):
    user_id: UUID
    file_path: str

class FileResponse(FileBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
