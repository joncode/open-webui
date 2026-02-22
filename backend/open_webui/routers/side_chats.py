"""
Side chat endpoints for Jaco.

Provides REST endpoints for creating, messaging, combining, and
discarding side chats attached to specific steps.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from open_webui.internal.db import get_session
from open_webui.models.side_chats import (
    SideChats,
    SideChatModel,
    SideChatMessageModel,
    CreateSideChatForm,
    AddSideChatMessageForm,
)
from open_webui.utils.auth import get_verified_user
from open_webui.utils.side_chat_combiner import generate_combined_step

log = logging.getLogger(__name__)

router = APIRouter()


############################
# Create a side chat
############################


@router.post("/", response_model=Optional[SideChatModel])
async def create_side_chat(
    form: CreateSideChatForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    result = SideChats.create_side_chat(
        chat_id=form.chat_id,
        user_id=user.id,
        step_index=form.step_index,
        original_step_content=form.original_step_content,
        db=db,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create side chat",
        )
    return result


############################
# List side chats for a chat
############################


@router.get("/by-chat/{chat_id}", response_model=list[SideChatModel])
async def list_side_chats(
    chat_id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    return SideChats.get_side_chats_by_chat_id(chat_id, db=db)


############################
# Add message to side chat
############################


@router.post("/{id}/messages", response_model=Optional[SideChatMessageModel])
async def add_message(
    id: str,
    form: AddSideChatMessageForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    side_chat = SideChats.get_side_chat_by_id(id, db=db)
    if not side_chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Side chat not found",
        )
    if side_chat.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot add messages to a {side_chat.status} side chat",
        )

    result = SideChats.add_message(
        side_chat_id=id,
        role=form.role,
        content=form.content,
        db=db,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add message",
        )
    return result


############################
# Combine side chat back into main
############################


@router.post("/{id}/combine", response_model=Optional[SideChatModel])
async def combine_side_chat(
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    side_chat = SideChats.get_side_chat_by_id(id, db=db)
    if not side_chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Side chat not found",
        )
    if side_chat.status != "open":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot combine a {side_chat.status} side chat",
        )

    messages = SideChats.get_messages(id, db=db)
    message_dicts = [{"role": m.role, "content": m.content} for m in messages]

    combined_text = await generate_combined_step(
        original_step_content=side_chat.original_step_content,
        side_chat_messages=message_dicts,
    )

    if combined_text is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate combined step",
        )

    result = SideChats.update_status(
        side_chat_id=id,
        status="combined",
        combined_step_content=combined_text,
        db=db,
    )
    return result


############################
# Delete / discard side chat
############################


@router.delete("/{id}")
async def delete_side_chat(
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    side_chat = SideChats.get_side_chat_by_id(id, db=db)
    if not side_chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Side chat not found",
        )

    success = SideChats.delete_side_chat(id, db=db)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete side chat",
        )
    return {"status": "ok", "id": id}
