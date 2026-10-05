import pytest

from app.models import Role, TicketStatus
from app.ticket_rules import is_valid_transition, may_change_status

S = TicketStatus
ALL = list(TicketStatus)
VALID = {
    (S.OPEN, S.IN_PROGRESS),
    (S.IN_PROGRESS, S.RESOLVED),
    (S.RESOLVED, S.CLOSED),
    (S.RESOLVED, S.IN_PROGRESS),
}


@pytest.mark.parametrize("current", ALL)
@pytest.mark.parametrize("new", ALL)
def test_only_the_defined_transitions_are_valid(current, new):
    assert is_valid_transition(current, new) == ((current, new) in VALID)


def test_staff_may_make_any_valid_transition():
    for role in (Role.TECHNICIAN, Role.ADMIN):
        assert all(may_change_status(role, c, n) for c, n in VALID)


def test_requester_may_only_close_or_reopen_resolved_tickets():
    allowed = {(c, n) for c, n in VALID if may_change_status(Role.REQUESTER, c, n)}

    assert allowed == {(S.RESOLVED, S.CLOSED), (S.RESOLVED, S.IN_PROGRESS)}
