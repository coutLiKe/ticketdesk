from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.deps import CurrentUser, DbSession, require_roles
from app.models import Priority, Role, Ticket, TicketStatus, User
from app.schemas import (
    AssigneeUpdate,
    PriorityUpdate,
    StatusUpdate,
    TicketCreate,
    TicketPage,
    TicketRead,
)
from app.ticket_rules import is_valid_transition, may_change_status

router = APIRouter(prefix="/tickets", tags=["tickets"])

StaffUser = Annotated[User, Depends(require_roles(Role.TECHNICIAN, Role.ADMIN))]


def _escape_like(text: str) -> str:
    """Make %, _ and \\ match literally inside an ILIKE pattern."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def get_visible_ticket(db: DbSession, user: User, ticket_id: int) -> Ticket:
    """Load a ticket the user is allowed to see, or raise 404.

    Hidden tickets get 404, not 403: we don't confirm that someone else's ticket exists.
    This is the single place that implements 'requesters only see their own'.
    """
    stmt = (
        select(Ticket)
        .where(Ticket.id == ticket_id)
        .options(joinedload(Ticket.requester), joinedload(Ticket.assignee))
    )
    if not user.is_staff:
        stmt = stmt.where(Ticket.requester_id == user.id)
    ticket = db.scalar(stmt)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


def _ensure_not_closed(ticket: Ticket) -> None:
    if ticket.status == TicketStatus.CLOSED:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Closed tickets cannot be changed")


@router.post("", response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(data: TicketCreate, user: CurrentUser, db: DbSession) -> Ticket:
    ticket = Ticket(title=data.title, description=data.description, requester=user)
    db.add(ticket)
    db.commit()
    return ticket


@router.get("", response_model=TicketPage)
def list_tickets(
    user: CurrentUser,
    db: DbSession,
    status_: Annotated[TicketStatus | None, Query(alias="status")] = None,
    priority: Priority | None = None,
    assignee_id: int | None = None,
    unassigned: bool = False,
    requester_id: int | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TicketPage:
    conditions = []
    if not user.is_staff:
        # Scope first: whatever filters follow can only narrow what the user may see.
        conditions.append(Ticket.requester_id == user.id)
    if status_ is not None:
        conditions.append(Ticket.status == status_)
    if priority is not None:
        conditions.append(Ticket.priority == priority)
    if assignee_id is not None:
        conditions.append(Ticket.assignee_id == assignee_id)
    if unassigned:
        conditions.append(Ticket.assignee_id.is_(None))
    if requester_id is not None:
        conditions.append(Ticket.requester_id == requester_id)
    if q:
        pattern = f"%{_escape_like(q)}%"
        conditions.append(
            Ticket.title.ilike(pattern, escape="\\")
            | Ticket.description.ilike(pattern, escape="\\")
        )

    total = db.scalar(select(func.count(Ticket.id)).where(*conditions)) or 0
    items = db.scalars(
        select(Ticket)
        .where(*conditions)
        # joinedload fetches requester/assignee in the same query, avoiding one extra
        # query per ticket (the "N+1" problem).
        .options(joinedload(Ticket.requester), joinedload(Ticket.assignee))
        .order_by(Ticket.created_at.desc(), Ticket.id.desc())  # id breaks ties
        .limit(limit)
        .offset(offset)
    ).all()
    return TicketPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/{ticket_id}", response_model=TicketRead)
def read_ticket(ticket_id: int, user: CurrentUser, db: DbSession) -> Ticket:
    return get_visible_ticket(db, user, ticket_id)


@router.put("/{ticket_id}/status", response_model=TicketRead)
def update_status(ticket_id: int, data: StatusUpdate, user: CurrentUser, db: DbSession) -> Ticket:
    ticket = get_visible_ticket(db, user, ticket_id)
    if not is_valid_transition(ticket.status, data.status):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Cannot move a ticket from {ticket.status} to {data.status}",
        )
    if not may_change_status(user.role, ticket.status, data.status):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
    ticket.status = data.status
    db.commit()
    return ticket


@router.put("/{ticket_id}/priority", response_model=TicketRead)
def update_priority(ticket_id: int, data: PriorityUpdate, user: StaffUser, db: DbSession) -> Ticket:
    ticket = get_visible_ticket(db, user, ticket_id)
    _ensure_not_closed(ticket)
    ticket.priority = data.priority
    db.commit()
    return ticket


@router.put("/{ticket_id}/assignee", response_model=TicketRead)
def update_assignee(ticket_id: int, data: AssigneeUpdate, user: StaffUser, db: DbSession) -> Ticket:
    ticket = get_visible_ticket(db, user, ticket_id)
    _ensure_not_closed(ticket)
    if data.assignee_id is None:
        ticket.assignee = None
    else:
        assignee = db.get(User, data.assignee_id)
        if assignee is None or not assignee.is_active or not assignee.is_staff:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Assignee must be an active technician or admin",
            )
        ticket.assignee = assignee
    db.commit()
    return ticket
