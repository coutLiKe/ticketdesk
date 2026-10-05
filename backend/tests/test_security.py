from datetime import UTC, datetime, timedelta

import jwt

from app.config import settings
from app.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_is_not_the_password_and_verifies():
    hashed = hash_password("correct horse")

    assert hashed != "correct horse"
    assert verify_password("correct horse", hashed)
    assert not verify_password("wrong", hashed)


def test_same_password_hashes_differently_each_time():
    """Per-password random salt: two users with the same password get different hashes."""
    assert hash_password("same") != hash_password("same")


def test_token_round_trip():
    assert decode_access_token(create_access_token(42)) == 42


def test_token_does_not_contain_role_or_password():
    claims = jwt.decode(create_access_token(1), options={"verify_signature": False})

    assert set(claims) == {"sub", "iat", "exp"}


def test_tampered_token_is_rejected():
    token = create_access_token(1)
    head, payload, signature = token.split(".")

    assert decode_access_token(f"{head}.{payload}.{signature[:-2]}xx") is None


def test_token_signed_with_other_key_is_rejected():
    forged = jwt.encode(
        {"sub": "1", "exp": datetime.now(UTC) + timedelta(minutes=5)}, "x" * 32, "HS256"
    )

    assert decode_access_token(forged) is None


def test_expired_token_is_rejected():
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(UTC) - timedelta(seconds=1)},
        settings.secret_key,
        settings.jwt_algorithm,
    )

    assert decode_access_token(expired) is None


def test_unsigned_alg_none_token_is_rejected():
    """Classic JWT attack: claim 'no signature needed'. Pinning algorithms blocks it."""
    unsigned = jwt.encode(
        {"sub": "1", "exp": datetime.now(UTC) + timedelta(minutes=5)}, None, "none"
    )

    assert decode_access_token(unsigned) is None


def test_garbage_is_rejected():
    assert decode_access_token("not-a-jwt") is None
