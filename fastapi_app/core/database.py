from sqlalchemy import create_engine, text, inspect
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

    Base.metadata.create_all(bind=engine)
    
    # SQLite schema migrations for existing tables
    try:
        inspector = inspect(engine)
        if "posts" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("posts")]
            if "image" not in columns:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE posts ADD COLUMN image VARCHAR(500)"))
                    conn.commit()

        if "users" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("users")]
            with engine.connect() as conn:
                if "subscription_plan_id" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN subscription_plan_id INTEGER REFERENCES subscription_plans(id)"))
                if "subscription_start_date" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN subscription_start_date DATETIME"))
                if "subscription_end_date" not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN subscription_end_date DATETIME"))
                conn.commit()
    except Exception:
        pass

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
