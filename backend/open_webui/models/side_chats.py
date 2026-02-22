"""
Side chat models for Jaco.

A side chat is a branched discussion that lets a user explore a tangent
on a specific step without disrupting the main chat flow. When the user
is done, they can combine (merge) the insights back into the original
step or discard the side chat entirely.

Tables:
    side_chat         – one row per side chat session
    side_chat_message – ordered messages within a side chat
"""

import logging
import time
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, Integer, String, Text, Index
from sqlalchemy.orm import Session

from open_webui.internal.db import Base, get_db_context

log = logging.getLogger(__name__)

SIDE_CHAT_STATUSES = {"open", "combined", "discarded"}


# ---------------------------------------------------------------------------
# SQLAlchemy ORM models
# ---------------------------------------------------------------------------


class SideChatRecord(Base):
    __tablename__ = "side_chat"

    id = Column(String, primary_key=True, unique=True)
    chat_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    step_index = Column(Integer, nullable=False)
    original_step_content = Column(Text, nullable=False)
    combined_step_content = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="open")
    created_at = Column(BigInteger, nullable=False)
    updated_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index("side_chat_chat_id_idx", "chat_id"),
        Index("side_chat_user_id_idx", "user_id"),
    )


class SideChatMessageRecord(Base):
    __tablename__ = "side_chat_message"

    id = Column(String, primary_key=True, unique=True)
    side_chat_id = Column(String, nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    ordering = Column(Integer, nullable=False, default=0)
    created_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        Index("side_chat_msg_side_chat_id_idx", "side_chat_id"),
    )


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class SideChatModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    chat_id: str
    user_id: str
    step_index: int
    original_step_content: str
    combined_step_content: Optional[str] = None
    status: str = "open"
    created_at: int = 0
    updated_at: int = 0


class SideChatMessageModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    side_chat_id: str
    role: str
    content: str
    ordering: int = 0
    created_at: int = 0


class CreateSideChatForm(BaseModel):
    chat_id: str
    step_index: int
    original_step_content: str


class AddSideChatMessageForm(BaseModel):
    role: str
    content: str


# ---------------------------------------------------------------------------
# CRUD class
# ---------------------------------------------------------------------------


class SideChatTable:
    def create_side_chat(
        self,
        chat_id: str,
        user_id: str,
        step_index: int,
        original_step_content: str,
        db: Optional[Session] = None,
    ) -> Optional[SideChatModel]:
        try:
            with get_db_context(db) as db:
                now = int(time.time())
                record = SideChatRecord(
                    id=str(uuid.uuid4()),
                    chat_id=chat_id,
                    user_id=user_id,
                    step_index=step_index,
                    original_step_content=original_step_content,
                    status="open",
                    created_at=now,
                    updated_at=now,
                )
                db.add(record)
                db.commit()
                db.refresh(record)
                return SideChatModel.model_validate(record)
        except Exception as e:
            log.error(f"Failed to create side chat: {e}")
            return None

    def get_side_chat_by_id(
        self,
        side_chat_id: str,
        db: Optional[Session] = None,
    ) -> Optional[SideChatModel]:
        try:
            with get_db_context(db) as db:
                record = db.get(SideChatRecord, side_chat_id)
                if record:
                    return SideChatModel.model_validate(record)
                return None
        except Exception as e:
            log.error(f"Failed to get side chat: {e}")
            return None

    def get_side_chats_by_chat_id(
        self,
        chat_id: str,
        db: Optional[Session] = None,
    ) -> list[SideChatModel]:
        try:
            with get_db_context(db) as db:
                records = (
                    db.query(SideChatRecord)
                    .filter(SideChatRecord.chat_id == chat_id)
                    .order_by(SideChatRecord.created_at.asc())
                    .all()
                )
                return [SideChatModel.model_validate(r) for r in records]
        except Exception as e:
            log.error(f"Failed to get side chats for chat: {e}")
            return []

    def add_message(
        self,
        side_chat_id: str,
        role: str,
        content: str,
        db: Optional[Session] = None,
    ) -> Optional[SideChatMessageModel]:
        try:
            with get_db_context(db) as db:
                # Get the next ordering value
                max_order = (
                    db.query(SideChatMessageRecord.ordering)
                    .filter(SideChatMessageRecord.side_chat_id == side_chat_id)
                    .order_by(SideChatMessageRecord.ordering.desc())
                    .first()
                )
                next_order = (max_order[0] + 1) if max_order else 0

                now = int(time.time())
                record = SideChatMessageRecord(
                    id=str(uuid.uuid4()),
                    side_chat_id=side_chat_id,
                    role=role,
                    content=content,
                    ordering=next_order,
                    created_at=now,
                )
                db.add(record)
                db.commit()
                db.refresh(record)
                return SideChatMessageModel.model_validate(record)
        except Exception as e:
            log.error(f"Failed to add side chat message: {e}")
            return None

    def get_messages(
        self,
        side_chat_id: str,
        db: Optional[Session] = None,
    ) -> list[SideChatMessageModel]:
        try:
            with get_db_context(db) as db:
                records = (
                    db.query(SideChatMessageRecord)
                    .filter(SideChatMessageRecord.side_chat_id == side_chat_id)
                    .order_by(SideChatMessageRecord.ordering.asc())
                    .all()
                )
                return [SideChatMessageModel.model_validate(r) for r in records]
        except Exception as e:
            log.error(f"Failed to get side chat messages: {e}")
            return []

    def update_status(
        self,
        side_chat_id: str,
        status: str,
        combined_step_content: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Optional[SideChatModel]:
        if status not in SIDE_CHAT_STATUSES:
            log.error(f"Invalid side chat status: {status}")
            return None
        try:
            with get_db_context(db) as db:
                record = db.get(SideChatRecord, side_chat_id)
                if not record:
                    return None
                record.status = status
                record.updated_at = int(time.time())
                if combined_step_content is not None:
                    record.combined_step_content = combined_step_content
                db.commit()
                db.refresh(record)
                return SideChatModel.model_validate(record)
        except Exception as e:
            log.error(f"Failed to update side chat status: {e}")
            return None

    def delete_side_chat(
        self,
        side_chat_id: str,
        db: Optional[Session] = None,
    ) -> bool:
        try:
            with get_db_context(db) as db:
                # Delete messages first
                db.query(SideChatMessageRecord).filter(
                    SideChatMessageRecord.side_chat_id == side_chat_id
                ).delete()
                # Delete the side chat
                count = (
                    db.query(SideChatRecord)
                    .filter(SideChatRecord.id == side_chat_id)
                    .delete()
                )
                db.commit()
                return count > 0
        except Exception as e:
            log.error(f"Failed to delete side chat: {e}")
            return False


SideChats = SideChatTable()
