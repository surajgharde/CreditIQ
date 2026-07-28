from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import config

# Default to local SQLite if no external postgres is defined
SQLALCHEMY_DATABASE_URL = config.DATABASE_URL or "sqlite:///./creditiq.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in SQLALCHEMY_DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
