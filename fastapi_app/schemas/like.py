from pydantic import BaseModel

class LikeOut(BaseModel):
    id: int
    post_id: int
    user_id: int

    class Config:
        from_attributes = True

class LikeToggleResponse(BaseModel):
    liked: bool
    likes_count: int
