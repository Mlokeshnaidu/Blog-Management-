from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from fastapi_app.schemas.user import UserOut

class UserStatsOverview(BaseModel):
    total_posts: int
    total_comments_made: int
    total_comments_received: int
    total_likes_received: int
    total_likes_given: int
    total_post_views: int
    avg_likes_per_post: float
    avg_comments_per_post: float
    engagement_rate: float

class PostAnalyticsItem(BaseModel):
    id: int
    title: str
    created_at: datetime
    views: int
    likes_count: int
    comments_count: int
    total_engagement: int

class TimeActivityPoint(BaseModel):
    date: str
    posts: int
    views: int
    likes: int
    comments: int

class QuotaUsage(BaseModel):
    plan_name: str
    posts_used: int
    posts_limit: int
    posts_percent: float
    likes_used: int
    likes_limit: int
    comments_used: int
    comments_limit: int

class EngagementDistribution(BaseModel):
    post_titles: List[str]
    likes_data: List[int]
    comments_data: List[int]
    views_data: List[int]

class UserDashboardResponse(BaseModel):
    user: UserOut
    overview: UserStatsOverview
    quota: QuotaUsage
    recent_posts: List[PostAnalyticsItem]
    top_posts: List[PostAnalyticsItem]
    timeline: List[TimeActivityPoint]
    distribution: EngagementDistribution
