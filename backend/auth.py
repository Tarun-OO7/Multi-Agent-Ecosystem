"""JWT authentication, password hashing, and RBAC."""
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel

JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_EXPIRE_MIN = int(os.environ.get("JWT_ACCESS_EXPIRE_MINUTES", "60"))
REFRESH_EXPIRE_DAYS = int(os.environ.get("JWT_REFRESH_EXPIRE_DAYS", "7"))

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

ROLES = {"admin", "auditor", "viewer"}
ROLE_HIERARCHY = {"admin": 3, "auditor": 2, "viewer": 1}


class TokenData(BaseModel):
    sub: str
    email: str
    role: str
    type: str = "access"


def hash_password(password: str) -> str:
    return pwd_ctx.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


def create_token(data: dict, expires_delta: timedelta, token_type: str = "access") -> str:
    to_encode = data.copy()
    to_encode.update({
        "exp": datetime.now(timezone.utc) + expires_delta,
        "iat": datetime.now(timezone.utc),
        "type": token_type,
    })
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_access_token(user_id: str, email: str, role: str) -> str:
    return create_token(
        {"sub": user_id, "email": email, "role": role},
        timedelta(minutes=ACCESS_EXPIRE_MIN),
        "access",
    )


def create_refresh_token(user_id: str, email: str, role: str) -> str:
    return create_token(
        {"sub": user_id, "email": email, "role": role},
        timedelta(days=REFRESH_EXPIRE_DAYS),
        "refresh",
    )


def decode_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return TokenData(
            sub=payload["sub"],
            email=payload["email"],
            role=payload["role"],
            type=payload.get("type", "access"),
        )
    except (JWTError, KeyError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> TokenData:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    td = decode_token(token)
    if td.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )
    return td


def require_role(min_role: str):
    """Dependency factory: ensures user has at least the required role level."""
    min_level = ROLE_HIERARCHY[min_role]

    async def checker(user: TokenData = Depends(get_current_user)) -> TokenData:
        if ROLE_HIERARCHY.get(user.role, 0) < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {min_role} or higher",
            )
        return user

    return checker
