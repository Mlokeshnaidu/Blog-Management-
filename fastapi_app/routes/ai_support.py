from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from fastapi_app.core.database import get_db
from fastapi_app.core.security import get_current_user
from fastapi_app.models.user import User
from fastapi_app.models.chat_message import ChatMessage
from fastapi_app.schemas.chat import ChatRequest, ChatResponse, ChatHistoryItem, ChatHistoryResponse
from fastapi_app.services.ai_support_service import get_ai_response

router = APIRouter(prefix="/api/ai-support", tags=["AI Support Chat"])


@router.post("/", response_model=ChatResponse)
def send_message(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Accept a user message, generate an AI response, log the conversation,
    and return the AI-generated reply.
    """
    ai_reply = get_ai_response(request.message)
    now = datetime.now(timezone.utc)

    # Log the chat message for activity tracking
    chat_log = ChatMessage(
        user_id=current_user.id,
        question=request.message,
        ai_response=ai_reply,
        created_at=now,
    )
    db.add(chat_log)
    db.commit()
    db.refresh(chat_log)

    return ChatResponse(
        user_message=request.message,
        ai_response=ai_reply,
        timestamp=now,
    )


@router.get("/history", response_model=ChatHistoryResponse)
def get_chat_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve the authenticated user's chat history, newest first.
    """
    query = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.desc())
    )
    total = query.count()
    messages = query.limit(min(limit, 200)).all()

    return ChatHistoryResponse(
        total=total,
        messages=[
            ChatHistoryItem(
                id=m.id,
                question=m.question,
                ai_response=m.ai_response,
                created_at=m.created_at,
            )
            for m in reversed(messages)  # Return in chronological order
        ],
    )
