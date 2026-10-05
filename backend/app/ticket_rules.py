"""Business rules for tickets, kept free of database and HTTP code so they are easy to test."""

from app.models import Role, TicketStatus

S = TicketStatus

# The ticket lifecycle as a state machine: current status -> statuses it may move to.
# CLOSED is terminal. A resolved ticket can be reopened (back to in_progress).
TRANSITIONS: dict[TicketStatus, set[TicketStatus]] = {
    S.OPEN: {S.IN_PROGRESS},
    S.IN_PROGRESS: {S.RESOLVED},
    S.RESOLVED: {S.CLOSED, S.IN_PROGRESS},
    S.CLOSED: set(),
}

# What the person who raised the ticket may do: confirm the fix, or say it isn't fixed.
REQUESTER_TRANSITIONS: set[tuple[TicketStatus, TicketStatus]] = {
    (S.RESOLVED, S.CLOSED),
    (S.RESOLVED, S.IN_PROGRESS),
}


def is_valid_transition(current: TicketStatus, new: TicketStatus) -> bool:
    return new in TRANSITIONS[current]


def may_change_status(role: Role, current: TicketStatus, new: TicketStatus) -> bool:
    """Assumes the transition itself is valid. Staff may make any valid one."""
    if role in (Role.TECHNICIAN, Role.ADMIN):
        return True
    return (current, new) in REQUESTER_TRANSITIONS
