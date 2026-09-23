from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from fastapi_app.core.database import get_db
from fastapi_app.core.security import get_current_user
from fastapi_app.core.subscription_service import check_can_like
from fastapi_app.services.notification_service import notification_service
from fastapi_app.models.user import User
from fastapi_app.models.post import Post
from fastapi_app.models.like import Like
from fastapi_app.models.notification import Notification
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
    check_can_like(current_user, db)

    new_like = Like(post_id=post_id, user_id=current_user.id)
    db.add(new_like)
    db.commit()
    db.refresh(post)

    # Trigger asynchronous email notification if post has an author and it's not self-like
    if post.author and post.author_id != current_user.id:
        notification_service.send_like_notification(
            post_title=post.title,
            recipient_email=post.author.email,
            recipient_name=post.author.username,
            actor_name=current_user.username,
            background_tasks=background_tasks,
        )

        # Create in-app notification for the post author
        in_app_notif = Notification(
            user_id=post.author_id,
            message=f'{current_user.username} liked your post "{post.title}"',
            notification_type="like",
        )
        db.add(in_app_notif)
        db.commit()

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
