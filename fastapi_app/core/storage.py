import os
import uuid
import shutil
from pathlib import Path
from fastapi import UploadFile, HTTPException, status

MEDIA_DIR = Path("media")
POSTS_MEDIA_DIR = MEDIA_DIR / "posts"
INVOICES_MEDIA_DIR = MEDIA_DIR / "invoices"

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/bmp",
    "application/octet-stream"  # Some test clients send octet-stream with valid image extensions
}

def init_storage():
    """Ensure media directories exist."""
    POSTS_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    INVOICES_MEDIA_DIR.mkdir(parents=True, exist_ok=True)

def save_upload_image(upload_file: UploadFile) -> str:
    """
    Validates and saves an uploaded image to media/posts/ with a unique filename.
    Returns the relative URL path: /media/posts/<filename>
    """
    init_storage()

    filename = upload_file.filename or "image.png"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid image format. Allowed formats: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    # Validate content-type if provided and not generic
    if upload_file.content_type and upload_file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content type: '{upload_file.content_type}'. Must be an image."
        )

    # Generate unique filename
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    destination_path = POSTS_MEDIA_DIR / unique_filename

    try:
        with open(destination_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded image: {str(e)}"
        )
    finally:
        upload_file.file.close()

    return f"/media/posts/{unique_filename}"

def delete_image_file(image_url: str):
    """Safely delete image file from disk given its /media/posts/... URL."""
    if not image_url or not image_url.startswith("/media/posts/"):
        return

    filename = os.path.basename(image_url)
    target_path = POSTS_MEDIA_DIR / filename
    try:
        if target_path.is_file():
            target_path.unlink()
    except Exception:
        pass
