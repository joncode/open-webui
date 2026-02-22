"""
Topic boundaries model for Jaco's auto-topic-split feature.

Records each topic split event, linking the original chat to the
newly created chat with metadata about when/why the split occurred.
"""

import logging
import time
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Float, String, Text, Index
from sqlalchemy.orm import Session

from open_webui.internal.db import Base, get_db, get_db_context

log = logging.getLogger(__name__)


class TopicBoundaryRecord(Base):
    __tablename__ = "topic_boundary"

    id = Column(String, primary_key=True, unique=True)
    original_chat_id = Column(String, nullable=False)
    new_chat_id = Column(String, nullable=False)
    triggering_message = Column(Text, nullable=False)
    old_topic = Column(Text, nullable=True)
    new_topic = Column(Text, nullable=True)
    confidence = Column(Float, default=0.0)
    split_timestamp = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index("topic_boundary_original_idx", "original_chat_id"),
        Index("topic_boundary_new_idx", "new_chat_id"),
    )


class TopicBoundaryModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_chat_id: str
    new_chat_id: str
    triggering_message: str
    old_topic: Optional[str] = None
    new_topic: Optional[str] = None
    confidence: float = 0.0
    split_timestamp: int = 0


class TopicBoundaryTable:
    def insert_boundary(
        self,
        original_chat_id: str,
        new_chat_id: str,
        triggering_message: str,
        old_topic: str = "",
        new_topic: str = "",
        confidence: float = 0.0,
        db: Optional[Session] = None,
    ) -> Optional[TopicBoundaryModel]:
        try:
            with get_db_context(db) as db:
                record = TopicBoundaryRecord(
                    id=str(uuid.uuid4()),
                    original_chat_id=original_chat_id,
                    new_chat_id=new_chat_id,
                    triggering_message=triggering_message,
                    old_topic=old_topic,
                    new_topic=new_topic,
                    confidence=confidence,
                    split_timestamp=int(time.time()),
                )
                db.add(record)
                db.commit()
                db.refresh(record)
                return TopicBoundaryModel.model_validate(record)
        except Exception as e:
            log.error(f"Failed to insert topic boundary: {e}")
            return None

    def get_boundaries_by_chat_id(
        self,
        chat_id: str,
        db: Optional[Session] = None,
    ) -> list[TopicBoundaryModel]:
        try:
            with get_db_context(db) as db:
                records = (
                    db.query(TopicBoundaryRecord)
                    .filter(
                        (TopicBoundaryRecord.original_chat_id == chat_id)
                        | (TopicBoundaryRecord.new_chat_id == chat_id)
                    )
                    .order_by(TopicBoundaryRecord.split_timestamp.asc())
                    .all()
                )
                return [TopicBoundaryModel.model_validate(r) for r in records]
        except Exception as e:
            log.error(f"Failed to get topic boundaries: {e}")
            return []

    def get_splits_from_chat(
        self,
        original_chat_id: str,
        db: Optional[Session] = None,
    ) -> list[TopicBoundaryModel]:
        try:
            with get_db_context(db) as db:
                records = (
                    db.query(TopicBoundaryRecord)
                    .filter(
                        TopicBoundaryRecord.original_chat_id == original_chat_id
                    )
                    .order_by(TopicBoundaryRecord.split_timestamp.asc())
                    .all()
                )
                return [TopicBoundaryModel.model_validate(r) for r in records]
        except Exception as e:
            log.error(f"Failed to get splits from chat: {e}")
            return []


TopicBoundaries = TopicBoundaryTable()
