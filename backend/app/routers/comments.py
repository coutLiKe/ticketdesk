from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.deps import CurrentUser, DbSession
from app.models import Comment, TicketStatus
from app.routers.tickets import get_visible_ticket
from app.schemas import CommentCreate, CommentRead

router = APIRouter(prefix="/tickets/{ticket_id}/comments", tags=["comments"])


@router.post("", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
def create_comment(ticket_id: int, data: CommentCreate, user: CurrentUser, db: DbSession):
    # Visibility first: a requester probing someone else's ticket gets 404 whatever they send.
    ticket = get_visible_ticket(db, user, ticket_id)
    if data.is_internal and not user.is_staff:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only staff can post internal notes")
    if ticket.status == TicketStatus.CLOSED:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Closed tickets cannot be changed")

    comment = Comment(ticket=ticket, author=user, body=data.body, is_internal=data.is_internal)
    db.add(comment)
    db.commit()
    return comment


@router.get("", response_model=list[CommentRead])
def list_comments(ticket_id: int, user: CurrentUser, db: DbSession):
    ticket = get_visible_ticket(db, user, ticket_id)
    stmt = (
        select(Comment)
        .where(Comment.ticket_id == ticket.id)
        .options(joinedload(Comment.author))  # one query instead of one per comment author
        .order_by(Comment.created_at, Comment.id)  # id breaks ties
    )
    if not user.is_staff:
        # Filtered in SQL, so internal notes never leave the database for a requester.
        stmt = stmt.where(Comment.is_internal.is_(False))
    return db.scalars(stmt).all()
