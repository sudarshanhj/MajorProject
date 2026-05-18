import uuid
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from database.db import Base

class RazorpayTransaction(Base):
    __tablename__ = "razorpay_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    razorpay_payment_id = Column(String, unique=True, index=True, nullable=False)
    razorpay_order_id = Column(String, index=True, nullable=False)
    razorpay_signature = Column(String, nullable=False)
    user_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    amount_inr = Column(Integer, nullable=False)
    credits_added = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def to_dict(self):
        return {
            "id": str(self.id),
            "payment_id": self.razorpay_payment_id,
            "order_id": self.razorpay_order_id,
            "user_id": str(self.user_id),
            "amount_inr": self.amount_inr,
            "credits_added": self.credits_added,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
