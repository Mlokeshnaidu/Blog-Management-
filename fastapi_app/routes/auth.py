from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi_app.core.database import get_db
from fastapi_app.core.security import verify_password, get_password_hash, create_access_token, get_current_user
from fastapi_app.models.user import User
from fastapi_app.schemas.user import UserRegister, UserLogin, UserOut, Token

router = APIRouter(prefix="/auth", tags=["Authentication"])

from fastapi_app.core.subscription_service import get_or_create_default_plan, subscribe_user_to_plan

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

@router.post(
    "/login",
    response_model=Token,
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/components/schemas/UserLogin"
                    }
                },
                "application/x-www-form-urlencoded": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "username": {"type": "string"},
                            "password": {"type": "string", "format": "password"}
                        },
                        "required": ["username", "password"]
                    }
                }
            }
        }
    }
)
async def login(request: Request, db: Session = Depends(get_db)):
    content_type = request.headers.get("content-type", "")
    username = None
    password = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            if isinstance(body, dict):
                username = body.get("username")
                password = body.get("password")
        except Exception:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid JSON body")
    elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        try:
            form = await request.form()
            username = form.get("username")
            password = form.get("password")
        except Exception:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid form data")
    else:
        try:
            body = await request.json()
            if isinstance(body, dict):
                username = body.get("username")
                password = body.get("password")
        except Exception:
            try:
                form = await request.form()
                username = form.get("username")
                password = form.get("password")
            except Exception:
                pass

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Username and password are required"
        )

    user = db.query(User).filter(
        (func.lower(User.username) == username.lower()) | (func.lower(User.email) == username.lower())
    ).first()
    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer", "user": user}

@router.get("/me", response_model=UserOut)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user
