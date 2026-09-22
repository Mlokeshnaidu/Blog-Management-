from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from fastapi_app.schemas.user import UserOut
from fastapi_app.schemas.comment import CommentOut

class PostCreate(BaseModel):
    title: str
    content: str

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

class PostOut(BaseModel):
    id: int
    title: str
    content: str
    image: Optional[str] = None
    author_id: int
    created_at: datetime
    author: Optional[UserOut] = None
    likes_count: int = 0
    comments_count: int = 0
    is_liked_by_me: bool = False

    class Config:
        from_attributes = True

class PostDetailOut(PostOut):
    comments: List[CommentOut] = []

class PaginatedPostResponse(BaseModel):
    items: List[PostOut]
    total: int
    page: int
    limit: int
    total_pages: int

