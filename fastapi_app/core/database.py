from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from fastapi_app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def init_db():
    from fastapi_app.models.subscription import SubscriptionPlan
    from fastapi_app.models.user import User
    from fastapi_app.models.notification import Notification
    from fastapi_app.models.chat_message import ChatMessage

    Base.metadata.create_all(bind=engine)

    # ── Migrate: add Auth0 columns to existing users table ────────────
    _migrations = [
        "ALTER TABLE users ADD COLUMN auth_provider VARCHAR(50) DEFAULT 'local'",
        "ALTER TABLE users ADD COLUMN auth_provider_id VARCHAR(255)",
    ]
    with engine.connect() as conn:
        for stmt in _migrations:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                # Column likely already exists — safe to ignore
                conn.rollback()

    # Seed Default Subscription Plans if empty
    db = SessionLocal()
    try:
        plans = [
            {
                "name": "Basic",
                "price": 0.0,
                "duration_days": 365,
                "max_posts": 1,
                "max_images_per_post": 1,
                "max_likes": 5,
                "max_comments": 5,
                "description": "Basic access with 1 post, 1 image upload, and up to 5 likes & comments."
            },
            {
                "name": "Premium",
                "price": 9.99,
                "duration_days": 30,
                "max_posts": 2,
                "max_images_per_post": 2,
                "max_likes": 20,
                "max_comments": 20,
                "description": "Premium access with 2 posts, 2 images per post, and up to 20 likes & comments."
            },
            {
                "name": "Pro",
                "price": 29.99,
                "duration_days": 30,
                "max_posts": -1,
                "max_images_per_post": -1,
                "max_likes": -1,
                "max_comments": -1,
                "description": "Pro unlimited access to all features (unlimited posts, images, likes & comments)."
            }
        ]

        for p_data in plans:
            existing = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == p_data["name"]).first()
            if not existing:
                plan = SubscriptionPlan(**p_data)
                db.add(plan)
        db.commit()

        # Update any users without a plan to Basic plan
        basic_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "Basic").first()
        if basic_plan:
            users_without_plan = db.query(User).filter(User.subscription_plan_id == None).all()
            for u in users_without_plan:
                u.subscription_plan_id = basic_plan.id
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
