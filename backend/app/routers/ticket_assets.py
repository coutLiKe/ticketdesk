from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.deps import CurrentUser, DbSession, StaffUser
from app.models import Asset, Ticket, TicketStatus, User, ticket_assets
from app.routers.tickets import get_visible_ticket
from app.schemas import AssetRead

router = APIRouter(prefix="/tickets/{ticket_id}/assets", tags=["ticket assets"])


def _linked_assets(db: DbSession, ticket: Ticket, user: User) -> list[Asset]:
    stmt = (
        select(Asset)
        .join(ticket_assets, ticket_assets.c.asset_id == Asset.id)
        .where(ticket_assets.c.ticket_id == ticket.id)
        .options(joinedload(Asset.assigned_user))
        .order_by(Asset.id)
    )
    if not user.is_staff:
        # Same rule as everywhere: a requester only ever sees assets assigned to them.
        stmt = stmt.where(Asset.assigned_user_id == user.id)
    return list(db.scalars(stmt))


def _ensure_open_for_changes(ticket: Ticket) -> None:
    if ticket.status == TicketStatus.CLOSED:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Closed tickets cannot be changed")


@router.get("", response_model=list[AssetRead])
def list_ticket_assets(ticket_id: int, user: CurrentUser, db: DbSession) -> list[Asset]:
    ticket = get_visible_ticket(db, user, ticket_id)
    return _linked_assets(db, ticket, user)


@router.put("/{asset_id}", response_model=list[AssetRead])
def link_asset(ticket_id: int, asset_id: int, user: StaffUser, db: DbSession) -> list[Asset]:
    ticket = get_visible_ticket(db, user, ticket_id)
    _ensure_open_for_changes(ticket)
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset not found")
    if asset not in ticket.assets:  # PUT is idempotent: linking twice is not an error
        ticket.assets.append(asset)
        db.commit()
    return _linked_assets(db, ticket, user)


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_asset(ticket_id: int, asset_id: int, user: StaffUser, db: DbSession) -> Response:
    ticket = get_visible_ticket(db, user, ticket_id)
    _ensure_open_for_changes(ticket)
    asset = db.get(Asset, asset_id)
    if asset is None or asset not in ticket.assets:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Asset is not linked to this ticket")
    ticket.assets.remove(asset)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
