import hashlib
import os
import base64
import secrets
import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database import get_db, User

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "smart_flashcard_super_secret_key_2026_dev_prod")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 1 week token expiration

security = HTTPBearer()

def hash_password(password: str) -> str:
    """Hash password using PBKDF2 with SHA-256."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    salt_b64 = base64.b64encode(salt).decode('utf-8')
    key_b64 = base64.b64encode(key).decode('utf-8')
    return f"pbkdf2_sha256${salt_b64}${key_b64}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password by rebuilding hash with the stored salt."""
    try:
        parts = hashed_password.split('$')
        if len(parts) != 3 or parts[0] != "pbkdf2_sha256":
            return False
        
        salt = base64.b64decode(parts[1].encode('utf-8'))
        stored_key = base64.b64decode(parts[2].encode('utf-8'))
        
        # Hash plain password with stored salt
        key = hashlib.pbkdf2_hmac('sha256', plain_password.encode('utf-8'), salt, 100000)
        return secrets.compare_digest(stored_key, key)
    except Exception:
        return False


def create_access_token(data: dict) -> str:
    """Generate JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    """Dependency to retrieve the logged-in user from the JWT token."""
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user
