import os

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./creditiq.db")
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "missing_key")
    AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY", "missing_key")
    AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY", "missing_key")
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "chroma_db")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    MAX_FILE_SIZE = os.getenv("MAX_FILE_SIZE", "10")
    JWT_SECRET = os.getenv("JWT_SECRET", "default_secret_for_dev_only")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

config = Config()
