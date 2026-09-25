from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from fastapi_app.schemas.subscription import SubscriptionPlanOut

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    auth_provider: Optional[str] = "local"
    subscription_plan_id: Optional[int] = None
    subscription_plan: Optional[SubscriptionPlanOut] = None
    subscription_start_date: Optional[datetime] = None
    subscription_end_date: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
