from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from fastapi_app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)

    subscription_plan_id = Column(Integer, ForeignKey("subscription_plans.id", ondelete="SET NULL"), nullable=True)
    subscription_start_date = Column(DateTime, nullable=True)
    subscription_end_date = Column(DateTime, nullable=True)

    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="user", cascade="all, delete-orphan")
    subscription_plan = relationship("SubscriptionPlan", back_populates="users")
    billing_histories = relationship("BillingHistory", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")
