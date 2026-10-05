"""Ticket comments. YOUR MILESTONE: implement the two routes below.

Read docs/M4-comments-spec.md first, then make `pytest tests/test_comments.py` pass.
Look at routers/tickets.py for the patterns to follow (especially get_visible_ticket).
"""

from fastapi import APIRouter, HTTPException, status

from app.deps import CurrentUser, DbSession
from app.schemas import CommentCreate, CommentRead

router = APIRouter(prefix="/tickets/{ticket_id}/comments", tags=["comments"])


@router.post("", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
def create_comment(ticket_id: int, data: CommentCreate, user: CurrentUser, db: DbSession):
    # TODO(you): implement. See docs/M4-comments-spec.md, "POST".
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.get("", response_model=list[CommentRead])
def list_comments(ticket_id: int, user: CurrentUser, db: DbSession):
    # TODO(you): implement. See docs/M4-comments-spec.md, "GET".
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")
