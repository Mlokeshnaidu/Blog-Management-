from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from fastapi_app.core.database import get_db
from fastapi_app.core.security import get_current_user
from fastapi_app.core.subscription_service import check_can_comment
from fastapi_app.services.notification_service import notification_service
from fastapi_app.models.user import User
from fastapi_app.models.post import Post
from fastapi_app.models.comment import Comment
from fastapi_app.models.notification import Notification
from fastapi_app.schemas.comment import CommentCreate, CommentOut

router = APIRouter(prefix="/posts", tags=["Comments"])

@router.get("/{post_id}/comments", response_model=List[CommentOut])
def get_comments(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post.comments

@router.post("/{post_id}/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(
    post_id: int,
    comment_in: CommentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Enforce Subscription Plan Limit for Comments
    check_can_comment(current_user, db)

    comment = Comment(post_id=post_id, user_id=current_user.id, text=comment_in.text)
    db.add(comment)
    db.commit()
    db.refresh(comment)

    # Trigger asynchronous email notification if post has an author and it's not self-comment
    if post.author and post.author_id != current_user.id:
        notification_service.send_comment_notification(
            post_title=post.title,
            recipient_email=post.author.email,
            recipient_name=post.author.username,
            actor_name=current_user.username,
            comment_text=comment.text,
            background_tasks=background_tasks,
        )

        # Create in-app notification for the post author
        in_app_notif = Notification(
            user_id=post.author_id,
            message=f'{current_user.username} commented on your post "{post.title}"',
            notification_type="comment",
        )
        db.add(in_app_notif)
        db.commit()

    return comment

@router.delete("/{post_id}/comments/{comment_id}")
def delete_comment(
    post_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    comment = db.query(Comment).filter(Comment.id == comment_id, Comment.post_id == post_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id and comment.post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")

    db.delete(comment)
    db.commit()
    return {"message": "Comment deleted successfully"}
