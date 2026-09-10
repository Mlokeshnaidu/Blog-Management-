import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretjwtkeyforblogmanagement")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./blog.db")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
