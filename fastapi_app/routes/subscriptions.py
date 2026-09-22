from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from fastapi_app.core.database import get_db
from fastapi_app.core.security import get_current_user
from fastapi_app.models.user import User
from fastapi_app.models.subscription import SubscriptionPlan, BillingHistory
from fastapi_app.schemas.subscription import (
    SubscriptionPlanOut,
    SubscribeRequest,
    SubscribeResponse,
    BillingHistoryOut,
)
from fastapi_app.core.subscription_service import subscribe_user_to_plan

router = APIRouter(tags=["Subscriptions & Billing"])

@router.get("/subscriptions/plans", response_model=List[SubscriptionPlanOut])
def get_plans(db: Session = Depends(get_db)):
    """List all available subscription tiers and their limit quotas."""
    return db.query(SubscriptionPlan).order_by(SubscriptionPlan.price.asc()).all()

@router.post("/subscriptions/subscribe", response_model=SubscribeResponse)
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
    """Retrieve billing history for the authenticated user."""
    records = db.query(BillingHistory).filter(
        BillingHistory.user_id == current_user.id
    ).order_by(BillingHistory.created_at.desc()).all()
    return records
