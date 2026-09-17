import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from fastapi_app.models.user import User
from fastapi_app.models.post import Post
from fastapi_app.models.like import Like
from fastapi_app.models.comment import Comment
from fastapi_app.models.subscription import SubscriptionPlan, BillingHistory
from fastapi_app.core.invoices import generate_invoice_pdf

LIMIT_EXCEEDED_MESSAGE = "You’ve reached your plan limit. Kindly upgrade your plan to continue."

def get_or_create_default_plan(db: Session) -> SubscriptionPlan:
    """Gets the default Basic plan or creates it if not present."""
    basic = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "Basic").first()
    if not basic:
        basic = SubscriptionPlan(
            name="Basic",
            price=0.0,
            duration_days=365,
            max_posts=1,
            max_images_per_post=1,
            max_likes=5,
            max_comments=5,
            description="Basic access with 1 post, 1 image upload, and up to 5 likes & comments."
        )
        db.add(basic)
        db.commit()
        db.refresh(basic)
    return basic

def get_user_plan(user: User, db: Session) -> SubscriptionPlan:
    """Returns the user's active SubscriptionPlan, defaulting to Basic if none set."""
    if user.subscription_plan:
        return user.subscription_plan
    
    if user.subscription_plan_id:
        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == user.subscription_plan_id).first()
        if plan:
            return plan

    basic = get_or_create_default_plan(db)
    user.subscription_plan_id = basic.id
    db.commit()
    db.refresh(user)
    return basic

def check_can_create_post(user: User, db: Session) -> SubscriptionPlan:
    """
    Model-level check: verifies whether user is allowed to create another post.
    Raises HTTP 403 if post limit is reached.
    """
    plan = get_user_plan(user, db)
    if plan.max_posts != -1:
        current_posts = db.query(Post).filter(Post.author_id == user.id).count()
        if current_posts >= plan.max_posts:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=LIMIT_EXCEEDED_MESSAGE
            )
    return plan

def check_image_limit(user: User, num_images: int, db: Session):
    """
    Model-level check: verifies whether the number of images to be uploaded per post
    exceeds the plan's max_images_per_post.
    """
    if num_images <= 0:
        return
    plan = get_user_plan(user, db)
    if plan.max_images_per_post != -1 and num_images > plan.max_images_per_post:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=LIMIT_EXCEEDED_MESSAGE
        )

def check_can_like(user: User, db: Session):
    """
    Model-level check: verifies whether user can add another like.
    Raises HTTP 403 if like limit is reached.
    """
    plan = get_user_plan(user, db)
    if plan.max_likes != -1:
        current_likes = db.query(Like).filter(Like.user_id == user.id).count()
        if current_likes >= plan.max_likes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=LIMIT_EXCEEDED_MESSAGE
            )

def check_can_comment(user: User, db: Session):
    """
    Model-level check: verifies whether user can add another comment.
    Raises HTTP 403 if comment limit is reached.
    """
    plan = get_user_plan(user, db)
    if plan.max_comments != -1:
        current_comments = db.query(Comment).filter(Comment.user_id == user.id).count()
        if current_comments >= plan.max_comments:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=LIMIT_EXCEEDED_MESSAGE
            )

def subscribe_user_to_plan(user: User, plan: SubscriptionPlan, db: Session) -> BillingHistory:
    """
    Subscribes/Upgrades a user to a given plan, creates a BillingHistory record,
    generates a ReportLab PDF invoice, and updates the user's active plan.
    """
    start_date = datetime.now(timezone.utc)
    end_date = start_date + timedelta(days=plan.duration_days)
    txn_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"

    # Generate PDF Invoice via ReportLab
    invoice_path = generate_invoice_pdf(
        user_name=user.username,
        plan_name=plan.name,
        price=plan.price,
        start_date=start_date,
        end_date=end_date,
        transaction_id=txn_id,
        user_email=user.email
    )

    billing = BillingHistory(
        user_id=user.id,
        plan_id=plan.id,
        plan_name=plan.name,
        amount=plan.price,
        transaction_id=txn_id,
        start_date=start_date,
        end_date=end_date,
        invoice_pdf_path=invoice_path,
        status="PAID"
    )
    db.add(billing)

    user.subscription_plan_id = plan.id
    user.subscription_start_date = start_date
    user.subscription_end_date = end_date

    db.commit()
    db.refresh(billing)
    db.refresh(user)
    return billing
