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
    Base.metadata.create_all(bind=engine)
    # Check and add 'image' column to posts table if missing (SQLite migration safety)
    try:
        inspector = inspect(engine)
        if "posts" in inspector.get_table_names():
            columns = [c["name"] for c in inspector.get_columns("posts")]
            if "image" not in columns:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE posts ADD COLUMN image VARCHAR(500)"))
                    conn.commit()
    except Exception:
        pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
