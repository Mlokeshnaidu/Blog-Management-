from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List

from fastapi_app.core.database import get_db
from fastapi_app.core.security import get_current_user
from fastapi_app.core.notifications import send_email_notification
from fastapi_app.models.user import User
from fastapi_app.models.post import Post
from fastapi_app.models.comment import Comment
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

    comment = Comment(post_id=post_id, user_id=current_user.id, text=comment_in.text)
    db.add(comment)
    db.commit()
    db.refresh(comment)

    if post.author and post.author_id != current_user.id:
        background_tasks.add_task(
            send_email_notification,
            recipient_email=post.author.email,
            recipient_username=post.author.username,
            subject=f"New comment on: {post.title}",
            message=f"@{current_user.username} commented: {comment.text}"
        )

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
