import uuid
import logging
from typing import Any
from sqlalchemy.orm import Session
from models.activity_log import ActivityLog
from flask import request

logger = logging.getLogger("DeepStegAI.Activity")

def log_user_activity(db: Session, user_id: Any, action: str, details: str = None, meta: dict = None):
    try:
        if user_id is not None and not isinstance(user_id, uuid.UUID):
            try:
                user_id = uuid.UUID(str(user_id))
            except (ValueError, TypeError):
                user_id = None
        
        ip = request.remote_addr if request else None
        new_log = ActivityLog(
            user_id=user_id,
            action=action,
            details=details,
            metadata_json=meta,
            ip_address=ip
        )
        db.add(new_log)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to log activity: {e}")
