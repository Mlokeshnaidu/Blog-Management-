from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi_app.core.database import engine, Base
import fastapi_app.models

from fastapi_app.routes.auth import router as auth_router
from fastapi_app.routes.posts import router as posts_router
from fastapi_app.routes.comments import router as comments_router
from fastapi_app.routes.likes import router as likes_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Blog Management API",
    description="Mini blogging system API built with FastAPI, SQLite, SQLAlchemy ORM, and JWT authentication.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

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


@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Welcome to the Blog Management API",
        "docs": "/docs",
        "redoc": "/redoc",
    }

