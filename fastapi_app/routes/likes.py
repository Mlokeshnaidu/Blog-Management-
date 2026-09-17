from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from fastapi_app.core.database import get_db
from fastapi_app.core.security import get_current_user
from fastapi_app.core.notifications import send_email_notification
from fastapi_app.models.user import User
from fastapi_app.models.post import Post
from fastapi_app.models.like import Like
from fastapi_app.schemas.like import LikeToggleResponse

router = APIRouter(prefix="/posts", tags=["Likes"])

@router.post("/{post_id}/like", response_model=LikeToggleResponse)
def toggle_like(
    post_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    existing_like = db.query(Like).filter(Like.post_id == post_id, Like.user_id == current_user.id).first()
    if existing_like:
        db.delete(existing_like)
        db.commit()
        return {"liked": False, "likes_count": len(post.likes)}

    # Enforce Subscription Plan Limit for Likes
    from fastapi_app.core.subscription_service import check_can_like
    check_can_like(current_user, db)

    new_like = Like(post_id=post_id, user_id=current_user.id)
    db.add(new_like)
    db.commit()
    db.refresh(post)

    if post.author and post.author_id != current_user.id:
        background_tasks.add_task(
            send_email_notification,
            recipient_email=post.author.email,
            recipient_username=post.author.username,
            subject=f"New like on: {post.title}",
            message=f"@{current_user.username} liked your post."
        )

    return {"liked": True, "likes_count": len(post.likes)}

@router.delete("/{post_id}/like", response_model=LikeToggleResponse)
def unlike(post_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    existing_like = db.query(Like).filter(Like.post_id == post_id, Like.user_id == current_user.id).first()
    if existing_like:
        db.delete(existing_like)
        db.commit()
        db.refresh(post)

    return {"liked": False, "likes_count": len(post.likes)}
