from pydantic import BaseModel
from datetime import datetime
from uuid import UUID
from typing import Optional

class CreditTransactionBase(BaseModel):
    amount: int
    transaction_type: str
    description: Optional[str] = None

class CreditTransactionCreate(CreditTransactionBase):
    user_id: UUID

class CreditTransactionResponse(CreditTransactionBase):
    id: UUID
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
