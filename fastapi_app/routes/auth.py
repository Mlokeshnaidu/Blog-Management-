from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session

from fastapi_app.core.database import get_db
from fastapi_app.core.security import verify_password, get_password_hash, create_access_token, get_current_user
from fastapi_app.core.subscription_service import get_or_create_default_plan, subscribe_user_to_plan
from fastapi_app.models.user import User
from fastapi_app.schemas.user import UserRegister, UserLogin, UserOut, Token

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(username=user_in.username, email=user_in.email, password=get_password_hash(user_in.password))
    db.add(user)
    db.commit()
    db.refresh(user)

    # Automatically enroll into Basic plan & generate welcome invoice
    basic_plan = get_or_create_default_plan(db)
    subscribe_user_to_plan(user, basic_plan, db)

    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer", "user": user}

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (func.lower(User.username) == form_data.username.lower()) | (func.lower(User.email) == form_data.username.lower())
    ).first()
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer", "user": user}

