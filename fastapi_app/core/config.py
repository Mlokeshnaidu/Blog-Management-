import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretjwtkeyforblogmanagement")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./blog.db")

    # SMTP / Mailtrap Email Configuration
    MAIL_SERVER: str = os.getenv("MAIL_SERVER", "sandbox.smtp.mailtrap.io")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", "2525"))
    MAIL_USERNAME: str = os.getenv("MAIL_USERNAME", "")
    MAIL_PASSWORD: str = os.getenv("MAIL_PASSWORD", "")
    MAIL_FROM: str = os.getenv("MAIL_FROM", "noreply@blogapp.com")
    MAIL_FROM_NAME: str = os.getenv("MAIL_FROM_NAME", "Blog Management System")
    MAIL_STARTTLS: bool = os.getenv("MAIL_STARTTLS", "True").lower() in ("true", "1", "yes")
    MAIL_SSL_TLS: bool = os.getenv("MAIL_SSL_TLS", "False").lower() in ("true", "1", "yes")
    USE_CREDENTIALS: bool = True
    VALIDATE_CERTS: bool = True
    MAIL_SUPPRESS_SEND: bool = os.getenv("MAIL_SUPPRESS_SEND", "False").lower() in ("true", "1", "yes")

    # Auth0 Configuration
    AUTH0_DOMAIN: str = os.getenv("AUTH0_DOMAIN", "your-tenant.auth0.com")
    AUTH0_CLIENT_ID: str = os.getenv("AUTH0_CLIENT_ID", "your-auth0-client-id")
    AUTH0_CLIENT_SECRET: str = os.getenv("AUTH0_CLIENT_SECRET", "your-auth0-client-secret")
    AUTH0_CALLBACK_URL: str = os.getenv("AUTH0_CALLBACK_URL", "http://localhost:8000/auth/callback")
    AUTH0_AUDIENCE: str = os.getenv("AUTH0_AUDIENCE", "")
    AUTH0_LOGOUT_REDIRECT: str = os.getenv("AUTH0_LOGOUT_REDIRECT", "http://localhost:8000/login")

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

