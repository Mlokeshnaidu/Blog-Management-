from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from fastapi_app.core.database import Base

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, index=True, nullable=False)  # "Basic", "Premium", "Pro"
    price = Column(Float, default=0.0, nullable=False)
    duration_days = Column(Integer, default=30, nullable=False)
    max_posts = Column(Integer, default=1, nullable=False)  # -1 for unlimited
    max_images_per_post = Column(Integer, default=1, nullable=False)  # -1 for unlimited
    max_likes = Column(Integer, default=5, nullable=False)  # -1 for unlimited
    max_comments = Column(Integer, default=5, nullable=False)  # -1 for unlimited
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    users = relationship("User", back_populates="subscription_plan")
    billing_records = relationship("BillingHistory", back_populates="plan")


class BillingHistory(Base):
    __tablename__ = "billing_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(Integer, ForeignKey("subscription_plans.id", ondelete="SET NULL"), nullable=True)
    plan_name = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    transaction_id = Column(String(100), unique=True, index=True, nullable=False)
    start_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    end_date = Column(DateTime, nullable=False)
    invoice_pdf_path = Column(String(500), nullable=False)
    status = Column(String(20), default="PAID", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="billing_histories")
    plan = relationship("SubscriptionPlan", back_populates="billing_records")
