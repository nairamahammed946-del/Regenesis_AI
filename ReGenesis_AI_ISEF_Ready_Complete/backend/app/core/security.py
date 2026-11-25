from datetime import datetime, timedelta, timezone
from typing import Optional, Union, Any
import jwt
import os
import base64
import hashlib
import hmac
try:
    import bcrypt
except ImportError:  # optional fallback for minimal/local environments
    bcrypt = None
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from backend.app.core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False)

def hash_password(password: str) -> str:
    """Secure password hashing using bcrypt."""
    pwd_bytes = password.encode("utf-8")
    if bcrypt is not None:
        # Pre-hash with SHA-256 to avoid bcrypt's 72-byte truncation for UTF-8 passwords.
        prehashed = hashlib.sha256(pwd_bytes).digest()
        salt = bcrypt.gensalt(rounds=12)
        return "bcrypt_sha256$" + bcrypt.hashpw(prehashed, salt).decode("utf-8")
    salt = os.urandom(16)
    iterations = 600_000
    digest = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt, iterations)
    return "pbkdf2_sha256${}${}${}".format(
        iterations, base64.urlsafe_b64encode(salt).decode(),
        base64.urlsafe_b64encode(digest).decode()
    )

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify raw password against bcrypt hash."""
    try:
        if hashed_password.startswith("pbkdf2_sha256$"):
            _, iterations, salt_b64, digest_b64 = hashed_password.split("$", 3)
            salt = base64.urlsafe_b64decode(salt_b64.encode())
            expected = base64.urlsafe_b64decode(digest_b64.encode())
            actual = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, int(iterations))
            return hmac.compare_digest(actual, expected)
        if hashed_password.startswith("bcrypt_sha256$"):
            encoded = hashed_password.split("$", 1)[1]
            prehashed = hashlib.sha256(plain_password.encode("utf-8")).digest()
            return bool(bcrypt and bcrypt.checkpw(prehashed, encoded.encode("utf-8")))
        # Backward compatibility for existing direct bcrypt hashes.
        return bool(bcrypt and bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8")))
    except Exception:
        return False

def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generate signed JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "exp": expire,
        "sub": str(subject),
        "iat": datetime.now(timezone.utc),
        "iss": settings.APP_NAME
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM], issuer=settings.APP_NAME)
        return payload
    except (jwt.PyJWTError, Exception):
        return None
