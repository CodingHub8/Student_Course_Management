import os
import hmac
import hashlib
import json
import base64
import time
from typing import Optional, Dict, Any

from fastapi import Request, HTTPException, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Secret key: read from environment variable or fall back to a dev default
# On Render.com, set APP_SECRET_KEY as an environment variable
SECRET_KEY = os.environ.get("APP_SECRET_KEY", "dev-fallback-secret-change-in-production")

ALGORITHM = "HS256"
TOKEN_EXPIRE_SECONDS = 7 * 24 * 3600  # 7 days


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def create_access_token(user: Dict[str, Any]) -> str:
    """Create a simple HMAC-signed JWT-like token."""
    header = _b64_encode(json.dumps({"alg": ALGORITHM, "typ": "JWT"}).encode())
    payload = {
        "sub": str(user.get("user_id", "")),
        "username": user.get("username", ""),
        "full_name": user.get("full_name", ""),
        "role": user.get("role", ""),
        "program": user.get("program", ""),
        "iat": int(time.time()),
        "exp": int(time.time()) + TOKEN_EXPIRE_SECONDS,
    }
    payload_enc = _b64_encode(json.dumps(payload).encode())
    signing_input = f"{header}.{payload_enc}".encode()
    signature = hmac.new(SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
    sig_enc = _b64_encode(signature)
    return f"{header}.{payload_enc}.{sig_enc}"


def _verify_token(token: str) -> Dict[str, Any]:
    """Verify a token and return its payload, or raise an exception."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid token format")
        header_enc, payload_enc, sig_enc = parts
        signing_input = f"{header_enc}.{payload_enc}".encode()
        expected_sig = hmac.new(SECRET_KEY.encode(), signing_input, hashlib.sha256).digest()
        provided_sig = _b64_decode(sig_enc)
        if not hmac.compare_digest(expected_sig, provided_sig):
            raise ValueError("Invalid signature")
        payload = json.loads(_b64_decode(payload_enc))
        if payload.get("exp", 0) < int(time.time()):
            raise ValueError("Token expired")
        return {
            "user_id": payload.get("sub"),
            "username": payload.get("username"),
            "full_name": payload.get("full_name"),
            "role": payload.get("role"),
            "program": payload.get("program"),
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


def _extract_token(request: Request) -> Optional[str]:
    """Extract token from Authorization header or session_token cookie."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    token = request.cookies.get("session_token")
    return token or None


async def get_current_user(request: Request) -> Dict[str, Any]:
    """FastAPI dependency: require a valid authenticated user."""
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated. Please log in.")
    return _verify_token(token)


async def get_optional_user(request: Request) -> Optional[Dict[str, Any]]:
    """FastAPI dependency: return user if authenticated, else None."""
    token = _extract_token(request)
    if not token:
        return None
    try:
        return _verify_token(token)
    except HTTPException:
        return None
