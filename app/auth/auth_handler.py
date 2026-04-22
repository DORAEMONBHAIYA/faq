import os
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
from jose import jwt
from passlib.context import CryptContext

# 🛡️ SECURITY: Always set JWT_SECRET in your .env for production!
SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY:
    # We provide a temporary one for development, but warn loudly
    SECRET_KEY = "DEV_ONLY_INSECURE_SECRET_CHANGE_ME"
    print("CRITICAL WARNING: JWT_SECRET not found in .env. Using insecure development key!")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 1 day

# Using sha256_crypt instead of bcrypt to avoid external dependency/binary issues in some environments
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        decoded_token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return decoded_token if decoded_token["exp"] >= time.time() else None
    except:
        return None
