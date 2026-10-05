from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Role, User
from app.security import decode_access_token

DbSession = Annotated[Session, Depends(get_db)]

# auto_error=False so WE decide the response and always answer 401 (not FastAPI's default).
bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
) -> User:
    """Authentication: who is making this request? Raises 401 if we can't tell."""
    if credentials is None:
        raise _unauthorized()
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise _unauthorized()
    user = db.get(User, user_id)
    # Loading the user on every request is what makes deactivation and role changes instant.
    if user is None or not user.is_active:
        raise _unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed: Role):
    """Authorization: is this user ALLOWED to do this? Raises 403 if not.

    Returns a dependency, so a route opts in with `Depends(require_roles(Role.ADMIN))`.
    """

    def checker(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user

    return checker
