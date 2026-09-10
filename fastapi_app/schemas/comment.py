from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from fastapi_app.schemas.user import UserOut

class CommentCreate(BaseModel):
    text: str

class CommentOut(BaseModel):
    id: int
    post_id: int
    user_id: int
    text: str
    created_at: datetime
    user: Optional[UserOut] = None

    class Config:
        from_attributes = True
