from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="User's message to the AI assistant")


class ChatResponse(BaseModel):
    user_message: str
    ai_response: str
    timestamp: datetime

    class Config:
        from_attributes = True


class ChatHistoryItem(BaseModel):
    id: int
    question: str
    ai_response: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    total: int
    messages: List[ChatHistoryItem]
