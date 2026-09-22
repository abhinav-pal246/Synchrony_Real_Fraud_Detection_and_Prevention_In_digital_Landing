"""
Security layer — JWT auth with credentials stored in PostgreSQL.

The login credential is NOT hardcoded and NOT in .env — it lives in the `users`
table as a bcrypt hash (seeded via scripts/seed_user.py). Only JWT signing config
comes from the environment.
"""

import os
import time

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .db import SessionLocal
from .models import User

JWT_SECRET = os.getenv("JWT_SECRET", "dev-insecure-change-me")
JWT_ALG = "HS256"
JWT_TTL = int(os.getenv("JWT_TTL_SECONDS", "3600"))

_bearer = HTTPBearer(auto_error=False)


def authenticate(email: str, password: str) -> bool:
    """Verify credentials against the bcrypt hash stored in Postgres."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.strip().lower()).first()
        if not user:
            return False
        try:
            return bcrypt.checkpw(password.encode(), user.password_hash.encode())
        except Exception:
            return False
    finally:
        db.close()


def create_access_token(subject: str) -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": subject, "iat": now, "exp": now + JWT_TTL},
        JWT_SECRET, algorithm=JWT_ALG,
    )


def get_current_user(cred: HTTPAuthorizationCredentials = Depends(_bearer)) -> str:
    if cred is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    try:
        payload = jwt.decode(cred.credentials, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    return payload.get("sub", "unknown")
