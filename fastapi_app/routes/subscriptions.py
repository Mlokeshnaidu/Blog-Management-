from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path

from fastapi_app.core.database import get_db
from fastapi_app.core.security import get_current_user
from fastapi_app.models.user import User
from fastapi_app.models.post import Post
from fastapi_app.models.like import Like
from fastapi_app.models.comment import Comment
from fastapi_app.models.subscription import SubscriptionPlan, BillingHistory
from fastapi_app.schemas.subscription import (
    SubscriptionPlanOut,
    SubscribeRequest,
    SubscribeResponse,
    BillingHistoryOut,
    UserPlanUsageOut
)
from fastapi_app.core.subscription_service import get_user_plan, subscribe_user_to_plan

router = APIRouter(tags=["Subscriptions & Billing"])

@router.get("/subscriptions/plans", response_model=List[SubscriptionPlanOut])
def get_plans(db: Session = Depends(get_db)):
    """List all available subscription tiers and their limit quotas."""
    return db.query(SubscriptionPlan).order_by(SubscriptionPlan.price.asc()).all()

@router.get("/subscriptions/my-plan", response_model=UserPlanUsageOut)
@router.get("/subscriptions/current", response_model=UserPlanUsageOut)
def get_my_plan(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's active subscription plan,
    usage metrics, and remaining feature limits.
    """
    plan = get_user_plan(current_user, db)

    posts_count = db.query(Post).filter(Post.author_id == current_user.id).count()
    likes_count = db.query(Like).filter(Like.user_id == current_user.id).count()
    comments_count = db.query(Comment).filter(Comment.user_id == current_user.id).count()

    can_create_post = (plan.max_posts == -1) or (posts_count < plan.max_posts)
    can_like = (plan.max_likes == -1) or (likes_count < plan.max_likes)
    can_comment = (plan.max_comments == -1) or (comments_count < plan.max_comments)

    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "plan_name": plan.name,
        "plan": plan,
        "posts_count": posts_count,
        "max_posts": plan.max_posts,
        "can_create_post": can_create_post,
        "likes_count": likes_count,
        "max_likes": plan.max_likes,
        "can_like": can_like,
        "comments_count": comments_count,
        "max_comments": plan.max_comments,
        "can_comment": can_comment,
        "max_images_per_post": plan.max_images_per_post,
        "subscription_start_date": current_user.subscription_start_date,
        "subscription_end_date": current_user.subscription_end_date
    }

@router.post("/subscriptions/subscribe", response_model=SubscribeResponse)
@router.post("/subscriptions/upgrade", response_model=SubscribeResponse)
def subscribe(
    payload: SubscribeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Subscribe or upgrade to a chosen plan (Basic, Premium, Pro).
    Generates a ReportLab PDF invoice and records the transaction in billing history.
    """
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.name.ilike(payload.plan_name.strip())
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription plan '{payload.plan_name}' not found. Available plans: Basic, Premium, Pro"
        )

    billing = subscribe_user_to_plan(current_user, plan, db)

    return {
        "message": f"Successfully subscribed to {plan.name} plan!",
        "plan": plan,
        "billing": billing
    }

@router.get("/billing/history", response_model=List[BillingHistoryOut])
def get_billing_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve billing history and generated PDF invoices for the authenticated user."""
    records = db.query(BillingHistory).filter(
        BillingHistory.user_id == current_user.id
    ).order_by(BillingHistory.created_at.desc()).all()
    return records

@router.get("/billing/invoices/{billing_id}/download")
@router.get("/billing/invoices/{billing_id}")
def download_invoice(
    billing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Download the generated PDF invoice for a specific billing transaction."""
    record = db.query(BillingHistory).filter(
        BillingHistory.id == billing_id,
        BillingHistory.user_id == current_user.id
    ).first()

    if not record:
        raise HTTPException(status_code=404, detail="Invoice record not found")

    pdf_rel_path = record.invoice_pdf_path.lstrip("/")
    file_path = Path(pdf_rel_path)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Invoice PDF file not found on disk")

    return FileResponse(
        path=str(file_path),
        filename=f"Invoice_{record.transaction_id}.pdf",
        media_type="application/pdf"
    )
