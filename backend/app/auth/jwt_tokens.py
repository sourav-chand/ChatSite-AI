"""RS256 JWT issuance + verification using a key pair on disk."""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError


@dataclass(slots=True, frozen=True)
class AccessClaims:
    user_id: UUID
    workspace_id: UUID
    role: str
    jti: str


def _read_key(path: str, private: bool) -> str:
    p = Path(path)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        p.write_bytes(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            if private
            else key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )
    return p.read_text(encoding="utf-8")


def get_private_key() -> str:
    return _read_key(settings.JWT_PRIVATE_KEY_PATH, private=True)


def get_public_key() -> str:
    return _read_key(settings.JWT_PUBLIC_KEY_PATH, private=False)


def issue_access_token(user_id: UUID, workspace_id: UUID, role: str) -> tuple[str, int]:
    now = int(time.time())
    ttl = settings.JWT_ACCESS_TTL_MIN * 60
    payload = {
        "sub": str(user_id),
        "ws": str(workspace_id),
        "role": role,
        "iat": now,
        "exp": now + ttl,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "jti": str(uuid4()),
    }
    token = jwt.encode(payload, get_private_key(), algorithm=settings.JWT_ALGORITHM)
    return token, ttl


def verify_access_token(token: str) -> AccessClaims:
    try:
        payload = jwt.decode(
            token,
            get_public_key(),
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
    except JWTError as e:
        raise UnauthorizedError(f"Invalid token: {e}") from e
    return AccessClaims(
        user_id=UUID(payload["sub"]),
        workspace_id=UUID(payload["ws"]),
        role=payload["role"],
        jti=payload["jti"],
    )


def issue_short_lived_token(subject: dict, ttl_seconds: int) -> str:
    now = int(time.time())
    payload = {
        **subject,
        "iat": now,
        "exp": now + ttl_seconds,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, get_private_key(), algorithm=settings.JWT_ALGORITHM)
