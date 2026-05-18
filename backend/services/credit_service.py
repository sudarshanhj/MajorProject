from sqlalchemy.orm import Session
from models.user import User
from models.credit_transaction import CreditTransaction
from typing import Optional
import uuid

class CreditService:
    @staticmethod
    def deduct_credits(db: Session, user_id: uuid.UUID, amount: int, description: str) -> Optional[int]:
        """
        Deducts credits from user and records the transaction.
        Returns the updated credit balance or None if insufficient funds.
        """
        # CRITICAL FIX: atomic SELECT FOR UPDATE lock
        user = db.query(User).filter(User.id == user_id).with_for_update().first()
        if not user or user.credits < amount:
            return None
        
        user.credits -= amount
        transaction = CreditTransaction(
            user_id=user_id,
            amount=-amount,
            transaction_type="usage",
            description=description
        )
        db.add(transaction)
        db.commit()
        db.refresh(user)
        return user.credits

    @staticmethod
    def add_credits(db: Session, user_id: uuid.UUID, amount: int, transaction_type: str, description: str) -> Optional[int]:
        """
        Adds credits to user and records the transaction.
        """
        # CRITICAL FIX: atomic SELECT FOR UPDATE lock
        user = db.query(User).filter(User.id == user_id).with_for_update().first()
        if not user:
            return None
        
        user.credits += amount
        
        transaction = CreditTransaction(
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type,
            description=description
        )
        db.add(transaction)
        db.commit()
        db.refresh(user)
        return user.credits
