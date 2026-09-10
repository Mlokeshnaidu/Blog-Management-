from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from fastapi_app.core.database import get_db
from fastapi_app.core.security import get_current_user, get_optional_current_user
from fastapi_app.models.user import User
from fastapi_app.models.post import Post
from fastapi_app.schemas.post import PostCreate, PostUpdate, PostOut, PostDetailOut

router = APIRouter(prefix="/posts", tags=["Posts"])

def _format_post(post: Post, current_user: Optional[User] = None):
    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "author_id": post.author_id,
        "created_at": post.created_at,
        "author": post.author,
        "likes_count": len(post.likes),
        "comments_count": len(post.comments),
        "is_liked_by_me": any(l.user_id == current_user.id for l in post.likes) if current_user else False,
        "comments": post.comments
    }

@router.get("", response_model=List[PostOut])
def get_posts(
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    query = db.query(Post)
    if q:
        query = query.filter((Post.title.ilike(f"%{q}%")) | (Post.content.ilike(f"%{q}%")))
    posts = query.order_by(Post.created_at.desc()).all()
    return [_format_post(p, current_user) for p in posts]

@router.get("/mine", response_model=List[PostOut])
def get_my_posts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    posts = db.query(Post).filter(Post.author_id == current_user.id).order_by(Post.created_at.desc()).all()
    return [_format_post(p, current_user) for p in posts]

@router.get("/{post_id}", response_model=PostDetailOut)
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return _format_post(post, current_user)

@router.post("", response_model=PostOut, status_code=status.HTTP_201_CREATED)
def create_post(
    post_in: PostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    post = Post(title=post_in.title, content=post_in.content, author_id=current_user.id)
    db.add(post)
    db.commit()
    db.refresh(post)
    return _format_post(post, current_user)

@router.put("/{post_id}", response_model=PostOut)
def update_post(
    post_id: int,
    post_in: PostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this post")

    if post_in.title is not None:
        post.title = post_in.title
    if post_in.content is not None:
        post.content = post_in.content

    db.commit()
    db.refresh(post)
    return _format_post(post, current_user)

@router.delete("/{post_id}")
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")

    db.delete(post)
    db.commit()
    return {"message": "Post deleted successfully"}
