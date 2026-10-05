from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import settings


def hash_password(password: str) -> str:
    """One-way hash with a random per-password salt (bcrypt embeds the salt in the result)."""
    salt = bcrypt.gensalt(rounds=settings.bcrypt_rounds)
    return bcrypt.hashpw(password.encode(), salt).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(user_id: int) -> str:
    """Signed token carrying only the user id ("sub") and issue/expiry times.

    The role is deliberately NOT in the token: we look the user up on every request, so a
    role change or deactivation takes effect immediately instead of when the token expires.
    """
    now = datetime.now(UTC)
    claims = {
        "sub": str(user_id),  # the JWT spec says "sub" is a string
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(claims, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int | None:
    """Return the user id if the token is valid and unexpired, otherwise None."""
    try:
        claims = jwt.decode(
            token,
            settings.secret_key,
            # Pin the allowed algorithm(s). Never let the token choose its own.
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub"]},
        )
        return int(claims["sub"])
    except (jwt.PyJWTError, ValueError):
        return None
