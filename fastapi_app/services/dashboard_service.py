from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func

from fastapi_app.models.post import Post
from fastapi_app.models.comment import Comment
from fastapi_app.models.like import Like


def get_dashboard_data(user_id: int, db: Session) -> dict:
    """
    Aggregate all dashboard metrics for a single user.

    Returns a dict ready to be serialised into DashboardResponse.
    """

    # ── Aggregate counts ───────────────────────────────────────────
    total_posts = db.query(func.count(Post.id)).filter(
        Post.author_id == user_id
    ).scalar() or 0

    total_comments = db.query(func.count(Comment.id)).filter(
        Comment.user_id == user_id
    ).scalar() or 0

    # Likes *received* on all of this user's posts
    total_likes_received = (
        db.query(func.count(Like.id))
        .join(Post, Like.post_id == Post.id)
        .filter(Post.author_id == user_id)
        .scalar()
    ) or 0

    # Total views (sum of view_count across user's posts)
    total_views = (
        db.query(func.coalesce(func.sum(Post.view_count), 0))
        .filter(Post.author_id == user_id)
        .scalar()
    ) or 0

    # ── Per-post breakdown (for bar / pie charts) ──────────────────
    user_posts = (
        db.query(Post)
        .filter(Post.author_id == user_id)
        .order_by(Post.created_at.desc())
        .all()
    )

    posts_stats = []
    for p in user_posts:
        likes_count = db.query(func.count(Like.id)).filter(Like.post_id == p.id).scalar() or 0
        comments_count = db.query(func.count(Comment.id)).filter(Comment.post_id == p.id).scalar() or 0
        posts_stats.append({
            "post_id": p.id,
            "title": p.title,
            "likes_count": likes_count,
            "comments_count": comments_count,
            "created_at": p.created_at,
        })

    # ── Activity over time (for line chart) ────────────────────────
    date_counts: dict[str, int] = defaultdict(int)
    for p in user_posts:
        day_str = p.created_at.strftime("%Y-%m-%d")
        date_counts[day_str] += 1

    activity_over_time = [
        {"date": d, "posts": c}
        for d, c in sorted(date_counts.items())
    ]

    return {
        "total_posts": total_posts,
        "total_comments": total_comments,
        "total_likes_received": total_likes_received,
        "total_views": total_views,
        "posts_stats": posts_stats,
        "activity_over_time": activity_over_time,
    }
