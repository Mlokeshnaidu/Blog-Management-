import math
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional

from fastapi_app.core.database import get_db
from fastapi_app.core.security import get_current_user, get_optional_current_user
from fastapi_app.core.storage import save_upload_image, delete_image_file
from fastapi_app.models.user import User
from fastapi_app.models.post import Post
from fastapi_app.schemas.post import PostOut, PostDetailOut, PaginatedPostResponse

router = APIRouter(prefix="/posts", tags=["Posts"])

def _format_post(post: Post, current_user: Optional[User] = None):
    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "image": post.image,
        "author_id": post.author_id,
        "created_at": post.created_at,
        "author": post.author,
        "likes_count": len(post.likes) if post.likes else 0,
        "comments_count": len(post.comments) if post.comments else 0,
        "is_liked_by_me": any(l.user_id == current_user.id for l in post.likes) if current_user and post.likes else False,
        "comments": post.comments or []
    }

@router.get("", response_model=PaginatedPostResponse)
def get_posts(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search keyword in title or content"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user)
):
    query = db.query(Post)
    if search and search.strip():
        term = search.strip()
        query = query.filter((Post.title.ilike(f"%{term}%")) | (Post.content.ilike(f"%{term}%")))

    total = query.count()
    total_pages = math.ceil(total / limit) if total > 0 else 0
    posts = query.order_by(Post.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "items": [_format_post(p, current_user) for p in posts],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }

@router.get("/mine", response_model=PaginatedPostResponse)
def get_my_posts(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search keyword in title or content"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Post).filter(Post.author_id == current_user.id)
    if search and search.strip():
        term = search.strip()
        query = query.filter((Post.title.ilike(f"%{term}%")) | (Post.content.ilike(f"%{term}%")))

    total = query.count()
    total_pages = math.ceil(total / limit) if total > 0 else 0
    posts = query.order_by(Post.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    return {
        "items": [_format_post(p, current_user) for p in posts],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }

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

@router.post("/create", response_model=PostOut, status_code=status.HTTP_201_CREATED)
@router.post("", response_model=PostOut, status_code=status.HTTP_201_CREATED)
def create_post(
    title: str = Form(..., description="Post title"),
    content: str = Form(..., description="Post body content"),
    image: Optional[UploadFile] = File(None, description="Cover image file (jpg, png, webp, etc.)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    image_url = None
    if image and image.filename:
        image_url = save_upload_image(image)

    post = Post(title=title, content=content, image=image_url, author_id=current_user.id)
    db.add(post)
    db.commit()
    db.refresh(post)
    return _format_post(post, current_user)

@router.put("/{post_id}/update", response_model=PostOut)
@router.put("/{post_id}", response_model=PostOut)
def update_post(
    post_id: int,
    title: Optional[str] = Form(None, description="New title"),
    content: Optional[str] = Form(None, description="New content"),
    image: Optional[UploadFile] = File(None, description="New cover image file"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this post")

    if title is not None:
        post.title = title
    if content is not None:
        post.content = content

    if image and image.filename:
        if post.image:
            delete_image_file(post.image)
        post.image = save_upload_image(image)

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

    if post.image:
        delete_image_file(post.image)

    db.delete(post)
    db.commit()
    return {"message": "Post deleted successfully"}
