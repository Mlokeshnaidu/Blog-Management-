"""
Authentication routes — Email/Password + Auth0 Social Login (Google & Facebook).
"""

import secrets
import httpx
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from fastapi_app.core.database import get_db
from fastapi_app.core.config import settings
from fastapi_app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
)
from fastapi_app.core.subscription_service import (
    get_or_create_default_plan,
    subscribe_user_to_plan,
)
from fastapi_app.models.user import User
from fastapi_app.schemas.user import UserRegister, UserLogin, UserOut, Token

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  1. Traditional Email / Password — Register & Login
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        username=user_in.username,
        email=user_in.email,
        password=get_password_hash(user_in.password),
        auth_provider="local",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Automatically enroll into Basic plan & generate welcome invoice
    basic_plan = get_or_create_default_plan(db)
    subscribe_user_to_plan(user, basic_plan, db)

    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
def signup(user_in: UserRegister, db: Session = Depends(get_db)):
    """Alias for /register — provides the /auth/signup endpoint requested by Rithika."""
    return register(user_in, db)


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (func.lower(User.username) == form_data.username.lower())
        | (func.lower(User.email) == form_data.username.lower())
    ).first()
    if not user or not user.password or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer", "user": user}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  2. Auth0 Social Login — Google & Facebook
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _build_auth0_authorize_url(connection: str, state: str) -> str:
    """Build the Auth0 /authorize redirect URL for a given social connection."""
    params = {
        "response_type": "code",
        "client_id": settings.AUTH0_CLIENT_ID,
        "redirect_uri": settings.AUTH0_CALLBACK_URL,
        "scope": "openid profile email",
        "state": state,
        "connection": connection,
    }
    if settings.AUTH0_AUDIENCE:
        params["audience"] = settings.AUTH0_AUDIENCE
    return f"https://{settings.AUTH0_DOMAIN}/authorize?{urlencode(params)}"


@router.get("/login/google", tags=["Social Login"])
def login_google():
    """Redirect the user to Auth0 → Google login."""
    state = secrets.token_urlsafe(32)
    return RedirectResponse(url=_build_auth0_authorize_url("google-oauth2", state))


@router.get("/login/facebook", tags=["Social Login"])
def login_facebook():
    """Redirect the user to Auth0 → Facebook login."""
    state = secrets.token_urlsafe(32)
    return RedirectResponse(url=_build_auth0_authorize_url("facebook", state))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  3. Auth0 Callback — Exchange code → tokens → user‑info → local session
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/callback")
async def auth0_callback(request: Request, db: Session = Depends(get_db)):
    """
    Auth0 redirects here after a successful social login.
    Steps:
      1. Exchange the authorization code for tokens.
      2. Fetch user info from Auth0.
      3. Find or create the local user.
      4. Issue a local JWT and redirect to the login page with the token.
    """
    code = request.query_params.get("code")
    error = request.query_params.get("error")
    error_description = request.query_params.get("error_description", "Authentication failed")

    if error:
        return RedirectResponse(url=f"/login?error={error_description}")
    if not code:
        return RedirectResponse(url="/login?error=Missing+authorization+code")

    # ── Step 1: Exchange code for tokens ──────────────────────────────────
    token_url = f"https://{settings.AUTH0_DOMAIN}/oauth/token"
    token_payload = {
        "grant_type": "authorization_code",
        "client_id": settings.AUTH0_CLIENT_ID,
        "client_secret": settings.AUTH0_CLIENT_SECRET,
        "code": code,
        "redirect_uri": settings.AUTH0_CALLBACK_URL,
    }

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(token_url, json=token_payload)

    if token_resp.status_code != 200:
        return RedirectResponse(url="/login?error=Token+exchange+failed")

    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        return RedirectResponse(url="/login?error=Invalid+token+response")

    # ── Step 2: Fetch user info ───────────────────────────────────────────
    userinfo_url = f"https://{settings.AUTH0_DOMAIN}/userinfo"
    async with httpx.AsyncClient() as client:
        userinfo_resp = await client.get(
            userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if userinfo_resp.status_code != 200:
        return RedirectResponse(url="/login?error=Failed+to+fetch+user+info")

    userinfo = userinfo_resp.json()
    auth0_sub = userinfo.get("sub", "")           # e.g. "google-oauth2|123456789"
    email = userinfo.get("email", "")
    name = userinfo.get("name") or userinfo.get("nickname") or email.split("@")[0]

    if not email:
        return RedirectResponse(url="/login?error=Email+not+provided+by+provider")

    # Determine provider
    provider = auth0_sub.split("|")[0] if "|" in auth0_sub else "auth0"

    # ── Step 3: Find or create local user ─────────────────────────────────
    user = db.query(User).filter(User.auth_provider_id == auth0_sub).first()
    if not user:
        # Check if email already exists (maybe from a normal signup)
        user = db.query(User).filter(User.email == email).first()
        if user:
            # Link existing account to social provider
            user.auth_provider = provider
            user.auth_provider_id = auth0_sub
            db.commit()
            db.refresh(user)
        else:
            # Brand‑new social user
            # Generate unique username from name
            base_username = name.replace(" ", "_").lower()[:40]
            username = base_username
            counter = 1
            while db.query(User).filter(User.username == username).first():
                username = f"{base_username}_{counter}"
                counter += 1

            user = User(
                username=username,
                email=email,
                password=None,
                auth_provider=provider,
                auth_provider_id=auth0_sub,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            # Enroll into Basic plan
            basic_plan = get_or_create_default_plan(db)
            subscribe_user_to_plan(user, basic_plan, db)

    # ── Step 4: Issue local JWT and redirect ──────────────────────────────
    local_token = create_access_token({"sub": user.username})

    # Redirect to login page with token in query string so the frontend
    # can store it and redirect to the dashboard.
    return RedirectResponse(
        url=f"/login?token={local_token}&provider={provider}",
        status_code=302,
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  4. Auth0 Logout
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/logout")
def logout():
    """
    Clear Auth0 session and redirect back to local login page.
    """
    params = {
        "client_id": settings.AUTH0_CLIENT_ID,
        "returnTo": settings.AUTH0_LOGOUT_REDIRECT,
    }
    return RedirectResponse(
        url=f"https://{settings.AUTH0_DOMAIN}/v2/logout?{urlencode(params)}"
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  5. Utility — Current User info (for dashboards, etc.)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user
