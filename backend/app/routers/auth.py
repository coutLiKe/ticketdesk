from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import DbSession
from app.models import Role, User
from app.ratelimit import per_client, per_email
from app.schemas import LoginRequest, TokenResponse, UserCreate, UserRead
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# Hash checked when the email doesn't exist, so "unknown email" takes as long as
# "wrong password" and response time doesn't reveal which emails are registered.
_DUMMY_HASH = hash_password("timing-equaliser")


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(data: UserCreate, db: DbSession) -> User:
    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role=Role.REQUESTER,  # always. Only an admin can promote someone later.
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # The UNIQUE constraint on email is the real guard: it also covers two
        # simultaneous signups that a "check first, then insert" approach would miss.
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Email already registered") from None
    return user


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, request: Request, db: DbSession) -> TokenResponse:
    client_key = f"{request.client.host if request.client else 'unknown'}|{data.email}"
    for counter, key in ((per_client, client_key), (per_email, data.email)):
        if counter.is_blocked(key):
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. Try again later.",
                headers={"Retry-After": str(counter.retry_after(key))},
            )

    user = db.scalar(select(User).where(User.email == data.email))
    password_ok = verify_password(data.password, user.hashed_password if user else _DUMMY_HASH)
    if user is None or not password_ok or not user.is_active:
        per_client.record(client_key)
        per_email.record(data.email)
        # One message for every failure: don't reveal which part was wrong.
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    per_client.reset(client_key)  # a successful login clears this client's failures
    return TokenResponse(access_token=create_access_token(user.id))
