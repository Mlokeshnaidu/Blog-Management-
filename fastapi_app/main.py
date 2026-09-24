from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from fastapi_app.core.database import init_db
from fastapi_app.core.storage import init_storage
import fastapi_app.models

from fastapi_app.routes.auth import router as auth_router
from fastapi_app.routes.posts import router as posts_router
from fastapi_app.routes.comments import router as comments_router
from fastapi_app.routes.likes import router as likes_router
from fastapi_app.routes.subscriptions import router as subscriptions_router
from fastapi_app.routes.dashboard import router as dashboard_router
from fastapi_app.routes.notifications import router as notifications_router
from fastapi_app.routes.ai_support import router as ai_support_router

init_db()
init_storage()

app = FastAPI(
    title="Blog Management API",
    description="Blogging system API built with FastAPI, SQLite, SQLAlchemy ORM, JWT authentication, subscription-based access control, email notifications, user dashboard, and AI support chat.",
    version="4.0.0",
    docs_url="/docs",
    redoc_url=None,
)

app.mount("/media", StaticFiles(directory="media"), name="media")

app.include_router(auth_router)
app.include_router(posts_router)
app.include_router(comments_router)
app.include_router(likes_router)
app.include_router(subscriptions_router)
app.include_router(dashboard_router)
app.include_router(notifications_router)
app.include_router(ai_support_router)


# ── Chat UI page ──────────────────────────────────────────────
import pathlib
from fastapi.responses import HTMLResponse

_TEMPLATE_DIR = pathlib.Path(__file__).resolve().parent / "templates"


@app.get("/chat", response_class=HTMLResponse, tags=["AI Support Chat"], include_in_schema=False)
def chat_page():
    """Serve the AI Support Chat UI."""
    html_path = _TEMPLATE_DIR / "chat.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to the Blog Management API",
        "docs": "/docs",
        "chat": "/chat",
    }

