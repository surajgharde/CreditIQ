from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from schemas.auth import UserResponse, Token
from utils.auth import verify_password, create_access_token, decode_token_email
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timezone
import secrets
from config import config

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """
    The authenticated user's email, from the bearer token.

    Every router that reads or writes borrower data depends on this. Before,
    only /api/analysis/draft and /api/profile looked at a token at all — and
    those two trusted an X-User-Email header that any caller could set — so
    upload, analyze, results, fraud, CAM, EWS and history were open to
    unauthenticated requests.

    Raises 401 on a missing, malformed or expired token.
    """
    email = decode_token_email(token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return email


# Registration is disabled for the admin-only prototype
# @router.post("/register", response_model=UserResponse)
# def register(user: UserCreate, db: Session = Depends(get_db)):
#     ...

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # The single administrator account, configured through ADMIN_EMAIL and
    # ADMIN_PASSWORD in .env. Both were hardcoded here as admin@gmail.com /
    # admin@123, so every deployment shipped with the same published password.
    # With either variable unset there is no admin account at all.
    if config.ADMIN_EMAIL and config.ADMIN_PASSWORD:
        # compare_digest on both halves: a plain == on the password leaks its
        # length and prefix through timing.
        email_matches = secrets.compare_digest(form_data.username, config.ADMIN_EMAIL)
        password_matches = secrets.compare_digest(form_data.password, config.ADMIN_PASSWORD)
        if email_matches and password_matches:
            access_token = create_access_token(data={"sub": config.ADMIN_EMAIL})
            return {"access_token": access_token, "token_type": "bearer"}

    # Standard DB check as fallback or if user management is implemented later
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def get_me(email: str = Depends(get_current_user), db: Session = Depends(get_db)):
    if config.ADMIN_EMAIL and email == config.ADMIN_EMAIL:
        # Synthetic record — the configured admin has no row in `users`.
        # Must satisfy every UserResponse field or FastAPI raises a 500.
        return {
            "email": config.ADMIN_EMAIL,
            "full_name": "System Administrator",
            "id": 0,
            "is_active": True,
            "created_at": datetime.now(timezone.utc)
        }
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
