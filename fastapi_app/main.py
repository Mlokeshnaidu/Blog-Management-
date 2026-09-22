from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles

from fastapi_app.core.database import init_db
from fastapi_app.core.storage import init_storage
import fastapi_app.models

from fastapi_app.routes.auth import router as auth_router
from fastapi_app.routes.posts import router as posts_router
from fastapi_app.routes.comments import router as comments_router
from fastapi_app.routes.likes import router as likes_router
from fastapi_app.routes.subscriptions import router as subscriptions_router
from fastapi_app.routes.admin import router as admin_router
from fastapi_app.routes.user_dashboard import router as user_dashboard_router

init_db()
init_storage()

app = FastAPI(
    title="Blog Management API with Subscription Access Control & User Analytics",
    description="Full-featured blogging system API built with FastAPI, SQLite, SQLAlchemy ORM, JWT authentication, tiered subscription-based access control (Basic, Premium, Pro), ReportLab PDF invoices, and User Analytics Dashboard.",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.mount("/media", StaticFiles(directory="media"), name="media")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(posts_router)
app.include_router(comments_router)
app.include_router(likes_router)
app.include_router(subscriptions_router)
app.include_router(admin_router)
app.include_router(user_dashboard_router)


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to the Blog Management & Analytics API",
        "docs": "/docs",
        "redoc": "/redoc",
        "admin_dashboard": "/admin",
        "user_dashboard": "/dashboard",
        "user_dashboard_api": "/user/dashboard"
    }
