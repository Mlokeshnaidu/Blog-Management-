from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

from fastapi_app.core.database import engine, Base
import fastapi_app.models

from fastapi_app.routes.auth import router as auth_router
from fastapi_app.routes.posts import router as posts_router
from fastapi_app.routes.comments import router as comments_router
from fastapi_app.routes.likes import router as likes_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Blog Management API", version="1.0.0")

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

frontend_path = Path(__file__).resolve().parent / "frontend"

if frontend_path.exists():
    app.mount("/js", StaticFiles(directory=str(frontend_path / "js")), name="js")

@app.get("/style.css", include_in_schema=False)
def serve_css():
    css_file = frontend_path / "style.css"
    return FileResponse(str(css_file), media_type="text/css")

@app.get("/", response_class=HTMLResponse, tags=["Frontend"])
def index():
    html_file = frontend_path / "index.html"
    return FileResponse(str(html_file)) if html_file.exists() else HTMLResponse("<h1>Blog Management API</h1>")
