from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class SubscriptionPlanOut(BaseModel):
    id: int
    name: str
    price: float
    duration_days: int
    max_posts: int
    max_images_per_post: int
    max_likes: int
    max_comments: int
    description: Optional[str] = None

    class Config:
        from_attributes = True

class SubscribeRequest(BaseModel):
    plan_name: str  # "Basic", "Premium", "Pro"

class BillingHistoryOut(BaseModel):
    id: int
    user_id: int
    plan_name: str
    amount: float
    transaction_id: str
    start_date: datetime
    end_date: datetime
    invoice_pdf_path: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class SubscribeResponse(BaseModel):
    message: str
    plan: SubscriptionPlanOut
    billing: BillingHistoryOut

class UserPlanUsageOut(BaseModel):
    user_id: int
    username: str
    plan_name: str
    plan: SubscriptionPlanOut
    posts_count: int
    max_posts: int
    can_create_post: bool
    likes_count: int
    max_likes: int
    can_like: bool
    comments_count: int
    max_comments: int
    can_comment: bool
    max_images_per_post: int
    subscription_start_date: Optional[datetime] = None
    subscription_end_date: Optional[datetime] = None
