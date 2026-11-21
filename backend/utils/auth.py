from datetime import datetime, timedelta
from typing import Optional
import jwt
import bcrypt
from config import config

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def decode_token_email(token: Optional[str]) -> Optional[str]:
    """
    The subject of a valid token, or None.

    Shared by the HTTP dependency in routers/auth.py and the WebSocket
    handshake check below, so both accept exactly the same tokens.
    """
    if not token:
        return None
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
    return payload.get("sub") or None


async def authenticate_websocket(websocket, token: Optional[str]) -> Optional[str]:
    """
    Authenticate a WebSocket from its `token` query parameter.

    A browser cannot set an Authorization header on a WebSocket handshake, so
    the token travels in the query string instead. Returns the email on
    success; on failure it closes the socket with 1008 (policy violation) and
    returns None, and the caller must return immediately.
    """
    email = decode_token_email(token)
    if email is None:
        await websocket.close(code=1008)
        return None
    return email


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)
    return encoded_jwt
