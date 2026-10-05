from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.deps import CurrentUser, DbSession, StaffUser
from app.models import Asset, AssetStatus, AssetType, Ticket, User, ticket_assets
from app.schemas import (
    AssetAssigneeUpdate,
    AssetCreate,
    AssetPage,
    AssetRead,
    AssetUpdate,
    TicketRead,
)
from app.utils import escape_like

router = APIRouter(prefix="/assets", tags=["assets"])


def get_visible_asset(db: DbSession, user: User, asset_id: int) -> Asset:
    """Staff see every asset. A requester sees only the ones assigned to them (others: 404)."""
    stmt = select(Asset).where(Asset.id == asset_id).options(joinedload(Asset.assigned_user))
    if not user.is_staff:
        stmt = stmt.where(Asset.assigned_user_id == user.id)
    asset = db.scalar(stmt)
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return asset


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def create_asset(data: AssetCreate, _: StaffUser, db: DbSession) -> Asset:
    asset = Asset(
        asset_tag=data.asset_tag,
        name=data.name,
        type=data.type,
        serial_number=data.serial_number,
    )
    db.add(asset)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Asset tag already exists") from None
    return asset


@router.get("", response_model=AssetPage)
def list_assets(
    user: CurrentUser,
    db: DbSession,
    type_: Annotated[AssetType | None, Query(alias="type")] = None,
    status_: Annotated[AssetStatus | None, Query(alias="status")] = None,
    assigned_user_id: int | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AssetPage:
    conditions = []
    if not user.is_staff:
        conditions.append(Asset.assigned_user_id == user.id)  # scope first
    if type_ is not None:
        conditions.append(Asset.type == type_)
    if status_ is not None:
        conditions.append(Asset.status == status_)
    if assigned_user_id is not None:
        conditions.append(Asset.assigned_user_id == assigned_user_id)
    if q:
        pattern = f"%{escape_like(q)}%"
        conditions.append(
            Asset.asset_tag.ilike(pattern, escape="\\")
            | Asset.name.ilike(pattern, escape="\\")
            | Asset.serial_number.ilike(pattern, escape="\\")
        )

    total = db.scalar(select(func.count(Asset.id)).where(*conditions)) or 0
    items = db.scalars(
        select(Asset)
        .where(*conditions)
        .options(joinedload(Asset.assigned_user))
        .order_by(Asset.created_at.desc(), Asset.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return AssetPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/{asset_id}", response_model=AssetRead)
def read_asset(asset_id: int, user: CurrentUser, db: DbSession) -> Asset:
    return get_visible_asset(db, user, asset_id)


@router.patch("/{asset_id}", response_model=AssetRead)
def update_asset(asset_id: int, data: AssetUpdate, user: StaffUser, db: DbSession) -> Asset:
    asset = get_visible_asset(db, user, asset_id)
    if data.name is not None:
        asset.name = data.name
    if data.type is not None:
        asset.type = data.type
    if data.serial_number is not None:
        asset.serial_number = data.serial_number
    db.commit()
    return asset


@router.put("/{asset_id}/assignee", response_model=AssetRead)
def assign_asset(asset_id: int, data: AssetAssigneeUpdate, user: StaffUser, db: DbSession) -> Asset:
    asset = get_visible_asset(db, user, asset_id)
    if asset.status == AssetStatus.RETIRED:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Retired assets cannot be assigned")
    if data.user_id is None:
        asset.assigned_user = None
        asset.status = AssetStatus.IN_STOCK
    else:
        assignee = db.get(User, data.user_id)
        if assignee is None or not assignee.is_active:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Assignee must be an active user"
            )
        asset.assigned_user = assignee
        asset.status = AssetStatus.ASSIGNED  # status always follows the assignment
    db.commit()
    return asset


@router.post("/{asset_id}/retire", response_model=AssetRead)
def retire_asset(asset_id: int, user: StaffUser, db: DbSession) -> Asset:
    asset = get_visible_asset(db, user, asset_id)
    if asset.status == AssetStatus.RETIRED:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Asset is already retired")
    asset.assigned_user = None
    asset.status = AssetStatus.RETIRED
    db.commit()
    return asset


@router.get("/{asset_id}/tickets", response_model=list[TicketRead])
def list_asset_tickets(asset_id: int, user: CurrentUser, db: DbSession) -> list[Ticket]:
    asset = get_visible_asset(db, user, asset_id)
    stmt = (
        select(Ticket)
        .join(ticket_assets, ticket_assets.c.ticket_id == Ticket.id)
        .where(ticket_assets.c.asset_id == asset.id)
        .options(joinedload(Ticket.requester), joinedload(Ticket.assignee))
        .order_by(Ticket.id.desc())
    )
    if not user.is_staff:
        stmt = stmt.where(Ticket.requester_id == user.id)  # only their own tickets
    return list(db.scalars(stmt))
