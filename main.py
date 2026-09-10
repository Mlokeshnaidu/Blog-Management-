"""
Root FastAPI entrypoint forwarding to fastapi_app.main.
Allows running with:
    uvicorn main:app --reload
    or
    uvicorn fastapi_app.main:app --reload
"""
from fastapi_app.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("fastapi_app.main:app", host="127.0.0.1", port=8000, reload=True)
