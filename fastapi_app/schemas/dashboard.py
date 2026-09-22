from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel


class PostStatItem(BaseModel):
    """Per-post statistics for chart data (likes/comments distribution)."""
    post_id: int
    title: str
    likes_count: int
    comments_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class ActivityTimePoint(BaseModel):
    """Single data point for the activity-over-time line chart."""
    date: str  # YYYY-MM-DD
    posts: int


class DashboardResponse(BaseModel):
    """Full dashboard response with all user-specific metrics."""
    user_id: int
    username: str

    # Aggregate counts
    total_posts: int
    total_comments: int
    total_likes_received: int
    total_views: int  # sum of view_count across all user posts

    # Per-post breakdown (for bar/pie charts)
    posts_stats: List[PostStatItem]

    # Activity over time (for line chart)
    activity_over_time: List[ActivityTimePoint]

    class Config:
        from_attributes = True
