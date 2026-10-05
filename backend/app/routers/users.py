from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession, require_roles
from app.models import Role, User
from app.schemas import UserAdminUpdate, UserRead

router = APIRouter(prefix="/users", tags=["users"])

AdminUser = Annotated[User, Depends(require_roles(Role.ADMIN))]


@router.get("/me", response_model=UserRead)
def read_me(user: CurrentUser) -> User:
    return user


@router.get("/assignable", response_model=list[UserRead])
def list_assignable_users(
    _: Annotated[User, Depends(require_roles(Role.TECHNICIAN, Role.ADMIN))], db: DbSession
) -> list[User]:
    """Who a ticket can be assigned to: active technicians and admins."""
    return list(
        db.scalars(
            select(User)
            .where(User.is_active.is_(True), User.role.in_([Role.TECHNICIAN, Role.ADMIN]))
            .order_by(User.full_name)
        )
    )


@router.get("", response_model=list[UserRead])
def list_users(_: AdminUser, db: DbSession) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)))


@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: int, data: UserAdminUpdate, admin: AdminUser, db: DbSession) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User not found")

    if target.id == admin.id and (data.role not in (None, Role.ADMIN) or data.is_active is False):
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="Admins cannot demote or deactivate themselves"
        )

    if data.role is not None:
        target.role = data.role
    if data.is_active is not None:
        target.is_active = data.is_active
    db.commit()
    return target
