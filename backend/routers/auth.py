from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from schemas.auth import UserCreate, UserLogin, UserResponse, Token
from utils.auth import get_password_hash, verify_password, create_access_token
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Optional
import jwt
from config import config

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# Registration is disabled for the admin-only prototype
# @router.post("/register", response_model=UserResponse)
# def register(user: UserCreate, db: Session = Depends(get_db)):
#     ...

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Predefined admin credentials for the prototype
    ADMIN_EMAIL = "admin@gmail.com"
    ADMIN_PASSWORD = "admin@123" # Simple password for prototype
    
    if form_data.username == ADMIN_EMAIL and form_data.password == ADMIN_PASSWORD:
        access_token = create_access_token(data={"sub": ADMIN_EMAIL})
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
def get_me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    

    if email == "admin@gmail.com":
        return {
            "email": "admin@gmail.com",
            "full_name": "System Administrator",
            "id": 0
        }
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
