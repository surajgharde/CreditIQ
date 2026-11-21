import os
import secrets

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./creditiq.db")
    # Admin credentials come from the environment. There is no default: the
    # email and password used to be literals in routers/auth.py
    # (admin@gmail.com / admin@123), which meant anyone who read the repository
    # could sign in to any deployment of it. With these unset, the admin login
    # is simply disabled and only database users can authenticate.
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "missing_key")
    AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY", "missing_key")
    AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY", "missing_key")
    CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "chroma_db")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    MAX_FILE_SIZE = os.getenv("MAX_FILE_SIZE", "10")
    # A shared literal default would let anyone holding the repository mint
    # valid tokens for a deployment that forgot to set JWT_SECRET. A random
    # per-process secret instead invalidates tokens on restart, which is
    # inconvenient in development and safe everywhere.
    JWT_SECRET = os.getenv("JWT_SECRET") or secrets.token_urlsafe(48)
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    # Browsers that may call the API. "*" with credentials is rejected by every
    # browser anyway, and allowing every origin to send cookies and bearer
    # tokens is the same as having no origin policy at all.
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ]

config = Config()
