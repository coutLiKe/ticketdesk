import pytest

from app.models import Priority, Role, TicketStatus

S = TicketStatus
STAFF = [Role.TECHNICIAN, Role.ADMIN]
NEW_TICKET = {"title": "VPN is down", "description": "Cannot connect since this morning"}


# ---- POST /tickets -------------------------------------------------------------------


def test_requester_creates_ticket_for_themselves(client, make_user, auth):
    user = make_user()

    response = client.post("/tickets", json=NEW_TICKET, headers=auth(user))

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "VPN is down"
    assert body["status"] == "open"
    assert body["priority"] == "medium"
    assert body["assignee"] is None
    assert body["requester"]["id"] == user.id


def test_create_ignores_fields_the_client_must_not_control(client, make_user, auth):
    """Mass-assignment attempt: status, priority, requester and assignee are server-controlled."""
    user = make_user()
    victim = make_user()
    payload = {
        **NEW_TICKET,
        "status": "closed",
        "priority": "urgent",
        "requester_id": victim.id,
        "assignee_id": victim.id,
    }

    body = client.post("/tickets", json=payload, headers=auth(user)).json()

    assert body["status"] == "open"
    assert body["priority"] == "medium"
    assert body["requester"]["id"] == user.id
    assert body["assignee"] is None


@pytest.mark.parametrize("role", STAFF)
def test_staff_can_also_create_tickets(client, make_user, auth, role):
    staff = make_user(role=role)

    assert client.post("/tickets", json=NEW_TICKET, headers=auth(staff)).status_code == 201


def test_create_requires_login(client):
    assert client.post("/tickets", json=NEW_TICKET).status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {"description": "no title"},
        {"title": "no description"},
        {"title": "", "description": "empty title"},
        {"title": "   ", "description": "blank title"},
        {"title": "x" * 201, "description": "title too long"},
    ],
)
def test_create_validates_input(client, make_user, auth, payload):
    assert client.post("/tickets", json=payload, headers=auth(make_user())).status_code == 422


# ---- GET /tickets: visibility ---------------------------------------------------------


def test_requester_sees_only_their_own_tickets(client, make_user, make_ticket, auth):
    me, other = make_user(), make_user()
    mine = make_ticket(me)
    make_ticket(other)

    body = client.get("/tickets", headers=auth(me)).json()

    assert [t["id"] for t in body["items"]] == [mine.id]
    assert body["total"] == 1


def test_requester_cannot_widen_scope_with_requester_filter(client, make_user, make_ticket, auth):
    me, other = make_user(), make_user()
    make_ticket(other)

    body = client.get(f"/tickets?requester_id={other.id}", headers=auth(me)).json()

    assert body["items"] == []


@pytest.mark.parametrize("role", STAFF)
def test_staff_see_all_tickets(client, make_user, make_ticket, auth, role):
    staff = make_user(role=role)
    make_ticket(make_user())
    make_ticket(make_user())

    assert client.get("/tickets", headers=auth(staff)).json()["total"] == 2


def test_list_requires_login(client):
    assert client.get("/tickets").status_code == 401


# ---- GET /tickets: filters, search, pagination ----------------------------------------


@pytest.fixture
def staff_headers(make_user, auth):
    return auth(make_user(role=Role.TECHNICIAN))


def ids(response):
    return {t["id"] for t in response.json()["items"]}


def test_filter_by_status(client, make_user, make_ticket, staff_headers):
    user = make_user()
    open_t = make_ticket(user)
    make_ticket(user, status=S.CLOSED)

    assert ids(client.get("/tickets?status=open", headers=staff_headers)) == {open_t.id}


def test_filter_by_priority(client, make_user, make_ticket, staff_headers):
    user = make_user()
    urgent = make_ticket(user, priority=Priority.URGENT)
    make_ticket(user, priority=Priority.LOW)

    assert ids(client.get("/tickets?priority=urgent", headers=staff_headers)) == {urgent.id}


def test_filter_by_assignee_and_unassigned(client, make_user, make_ticket, staff_headers):
    user = make_user()
    tech = make_user(role=Role.TECHNICIAN)
    assigned = make_ticket(user, assignee=tech)
    unassigned = make_ticket(user)

    assert ids(client.get(f"/tickets?assignee_id={tech.id}", headers=staff_headers)) == {
        assigned.id
    }
    assert ids(client.get("/tickets?unassigned=true", headers=staff_headers)) == {unassigned.id}


def test_staff_can_filter_by_requester(client, make_user, make_ticket, staff_headers):
    a, b = make_user(), make_user()
    ticket_a = make_ticket(a)
    make_ticket(b)

    assert ids(client.get(f"/tickets?requester_id={a.id}", headers=staff_headers)) == {ticket_a.id}


def test_filters_combine_with_and(client, make_user, make_ticket, staff_headers):
    user = make_user()
    match = make_ticket(user, status=S.OPEN, priority=Priority.HIGH)
    make_ticket(user, status=S.OPEN, priority=Priority.LOW)
    make_ticket(user, status=S.CLOSED, priority=Priority.HIGH)

    assert ids(client.get("/tickets?status=open&priority=high", headers=staff_headers)) == {
        match.id
    }


def test_search_matches_title_or_description_case_insensitively(
    client, make_user, make_ticket, staff_headers
):
    user = make_user()
    in_title = make_ticket(user, title="WiFi drops constantly")
    in_desc = make_ticket(user, title="Slow", description="the wifi is flaky")
    make_ticket(user, title="Printer", description="paper jam")

    assert ids(client.get("/tickets?q=WIFI", headers=staff_headers)) == {in_title.id, in_desc.id}


def test_search_treats_percent_and_underscore_literally(
    client, make_user, make_ticket, staff_headers
):
    user = make_user()
    literal = make_ticket(user, title="Disk 100% full")
    make_ticket(user, title="Disk fine")

    assert ids(client.get("/tickets?q=100%25", headers=staff_headers)) == {literal.id}
    assert ids(client.get("/tickets?q=_", headers=staff_headers)) == set()


def test_search_is_still_scoped_for_requesters(client, make_user, make_ticket, auth):
    me, other = make_user(), make_user()
    make_ticket(other, title="secret merger")

    assert client.get("/tickets?q=merger", headers=auth(me)).json()["items"] == []


def test_results_are_newest_first(client, make_user, make_ticket, staff_headers):
    user = make_user()
    first = make_ticket(user)
    second = make_ticket(user)

    body = client.get("/tickets", headers=staff_headers).json()

    assert [t["id"] for t in body["items"]] == [second.id, first.id]


def test_pagination(client, make_user, make_ticket, staff_headers):
    user = make_user()
    created = [make_ticket(user) for _ in range(5)]
    newest_first = [t.id for t in reversed(created)]

    page1 = client.get("/tickets?limit=2&offset=0", headers=staff_headers).json()
    page3 = client.get("/tickets?limit=2&offset=4", headers=staff_headers).json()

    assert [t["id"] for t in page1["items"]] == newest_first[:2]
    assert [t["id"] for t in page3["items"]] == newest_first[4:]
    assert page1["total"] == page3["total"] == 5
    assert page1["limit"] == 2 and page3["offset"] == 4


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "status=banana"])
def test_list_rejects_invalid_query_params(client, staff_headers, query):
    assert client.get(f"/tickets?{query}", headers=staff_headers).status_code == 422


# ---- GET /tickets/{id} ----------------------------------------------------------------


def test_requester_can_view_own_ticket_without_leaking_emails(client, make_user, make_ticket, auth):
    me = make_user()
    ticket = make_ticket(me)

    response = client.get(f"/tickets/{ticket.id}", headers=auth(me))

    assert response.status_code == 200
    assert response.json()["id"] == ticket.id
    assert "email" not in response.json()["requester"]


def test_requester_gets_404_for_someone_elses_ticket(client, make_user, make_ticket, auth):
    me, other = make_user(), make_user()
    ticket = make_ticket(other)

    assert client.get(f"/tickets/{ticket.id}", headers=auth(me)).status_code == 404


@pytest.mark.parametrize("role", STAFF)
def test_staff_can_view_any_ticket(client, make_user, make_ticket, auth, role):
    ticket = make_ticket(make_user())

    assert (
        client.get(f"/tickets/{ticket.id}", headers=auth(make_user(role=role))).status_code == 200
    )


def test_unknown_ticket_is_404(client, make_user, auth):
    assert client.get("/tickets/999999", headers=auth(make_user())).status_code == 404


def test_view_requires_login(client, make_user, make_ticket):
    ticket = make_ticket(make_user())

    assert client.get(f"/tickets/{ticket.id}").status_code == 401


# ---- PUT /tickets/{id}/status ---------------------------------------------------------


def put_status(client, ticket, status, headers):
    return client.put(f"/tickets/{ticket.id}/status", json={"status": status}, headers=headers)


@pytest.mark.parametrize("role", STAFF)
def test_staff_walk_a_ticket_through_its_lifecycle(client, make_user, make_ticket, auth, role):
    staff = auth(make_user(role=role))
    ticket = make_ticket(make_user())

    for status in ["in_progress", "resolved", "closed"]:
        response = put_status(client, ticket, status, staff)
        assert response.status_code == 200
        assert response.json()["status"] == status


@pytest.mark.parametrize(
    ("current", "new"),
    [
        (S.OPEN, "resolved"),
        (S.OPEN, "closed"),
        (S.OPEN, "open"),
        (S.IN_PROGRESS, "closed"),
        (S.CLOSED, "open"),
        (S.CLOSED, "in_progress"),
    ],
)
def test_invalid_transitions_are_409(client, make_user, make_ticket, staff_headers, current, new):
    ticket = make_ticket(make_user(), status=current)

    assert put_status(client, ticket, new, staff_headers).status_code == 409


def test_resolved_ticket_can_be_reopened_by_staff(client, make_user, make_ticket, staff_headers):
    ticket = make_ticket(make_user(), status=S.RESOLVED)

    assert (
        put_status(client, ticket, "in_progress", staff_headers).json()["status"] == "in_progress"
    )


@pytest.mark.parametrize("new", ["closed", "in_progress"])
def test_requester_can_close_or_reopen_own_resolved_ticket(
    client, make_user, make_ticket, auth, new
):
    me = make_user()
    ticket = make_ticket(me, status=S.RESOLVED)

    response = put_status(client, ticket, new, auth(me))

    assert response.status_code == 200
    assert response.json()["status"] == new


def test_requester_cannot_start_work_on_own_ticket(client, make_user, make_ticket, auth):
    me = make_user()
    ticket = make_ticket(me, status=S.OPEN)

    assert put_status(client, ticket, "in_progress", auth(me)).status_code == 403


def test_requester_cannot_resolve_own_ticket(client, make_user, make_ticket, auth):
    me = make_user()
    ticket = make_ticket(me, status=S.IN_PROGRESS)

    assert put_status(client, ticket, "resolved", auth(me)).status_code == 403


def test_requester_cannot_skip_the_flow_by_closing_an_open_ticket(
    client, make_user, make_ticket, auth
):
    me = make_user()
    ticket = make_ticket(me, status=S.OPEN)

    assert put_status(client, ticket, "closed", auth(me)).status_code == 409


def test_requester_cannot_change_status_of_someone_elses_ticket(
    client, make_user, make_ticket, auth
):
    ticket = make_ticket(make_user(), status=S.RESOLVED)

    assert put_status(client, ticket, "closed", auth(make_user())).status_code == 404


def test_status_update_requires_login(client, make_user, make_ticket):
    ticket = make_ticket(make_user())

    assert put_status(client, ticket, "in_progress", {}).status_code == 401


def test_status_update_unknown_ticket_is_404(client, staff_headers):
    response = client.put("/tickets/999999/status", json={"status": "open"}, headers=staff_headers)

    assert response.status_code == 404


def test_status_update_rejects_unknown_status(client, make_user, make_ticket, staff_headers):
    ticket = make_ticket(make_user())

    assert put_status(client, ticket, "banana", staff_headers).status_code == 422


# ---- PUT /tickets/{id}/priority -------------------------------------------------------


def put_priority(client, ticket, priority, headers):
    return client.put(
        f"/tickets/{ticket.id}/priority", json={"priority": priority}, headers=headers
    )


@pytest.mark.parametrize("role", STAFF)
def test_staff_can_set_priority(client, make_user, make_ticket, auth, role):
    ticket = make_ticket(make_user())

    response = put_priority(client, ticket, "urgent", auth(make_user(role=role)))

    assert response.status_code == 200
    assert response.json()["priority"] == "urgent"


def test_requester_cannot_set_priority_on_own_ticket(client, make_user, make_ticket, auth):
    me = make_user()
    ticket = make_ticket(me)

    assert put_priority(client, ticket, "urgent", auth(me)).status_code == 403


def test_requester_gets_403_setting_priority_on_others_ticket(client, make_user, make_ticket, auth):
    """Role is checked before the ticket is looked up, so existence is never revealed."""
    ticket = make_ticket(make_user())

    assert put_priority(client, ticket, "urgent", auth(make_user())).status_code == 403


def test_priority_update_requires_login(client, make_user, make_ticket):
    ticket = make_ticket(make_user())

    assert put_priority(client, ticket, "low", {}).status_code == 401


def test_priority_cannot_change_on_closed_ticket(client, make_user, make_ticket, staff_headers):
    ticket = make_ticket(make_user(), status=S.CLOSED)

    assert put_priority(client, ticket, "low", staff_headers).status_code == 409


def test_priority_rejects_unknown_value(client, make_user, make_ticket, staff_headers):
    ticket = make_ticket(make_user())

    assert put_priority(client, ticket, "whenever", staff_headers).status_code == 422


def test_priority_update_unknown_ticket_is_404(client, staff_headers):
    response = client.put(
        "/tickets/999999/priority", json={"priority": "low"}, headers=staff_headers
    )

    assert response.status_code == 404


# ---- PUT /tickets/{id}/assignee -------------------------------------------------------


def put_assignee(client, ticket, assignee_id, headers):
    return client.put(
        f"/tickets/{ticket.id}/assignee", json={"assignee_id": assignee_id}, headers=headers
    )


def test_technician_can_assign_ticket_to_themselves(client, make_user, make_ticket, auth):
    tech = make_user(role=Role.TECHNICIAN)
    ticket = make_ticket(make_user())

    response = put_assignee(client, ticket, tech.id, auth(tech))

    assert response.status_code == 200
    assert response.json()["assignee"]["id"] == tech.id


@pytest.mark.parametrize("assigner", STAFF)
@pytest.mark.parametrize("assignee_role", STAFF)
def test_staff_can_assign_to_any_technician_or_admin(
    client, make_user, make_ticket, auth, assigner, assignee_role
):
    ticket = make_ticket(make_user())
    target = make_user(role=assignee_role)

    response = put_assignee(client, ticket, target.id, auth(make_user(role=assigner)))

    assert response.status_code == 200
    assert response.json()["assignee"]["id"] == target.id


def test_assignee_null_unassigns(client, make_user, make_ticket, staff_headers):
    tech = make_user(role=Role.TECHNICIAN)
    ticket = make_ticket(make_user(), assignee=tech)

    response = put_assignee(client, ticket, None, staff_headers)

    assert response.status_code == 200
    assert response.json()["assignee"] is None


def test_cannot_assign_to_a_requester(client, make_user, make_ticket, staff_headers):
    ticket = make_ticket(make_user())

    assert put_assignee(client, ticket, make_user().id, staff_headers).status_code == 422


def test_cannot_assign_to_inactive_technician(client, make_user, make_ticket, staff_headers):
    ticket = make_ticket(make_user())
    gone = make_user(role=Role.TECHNICIAN, is_active=False)

    assert put_assignee(client, ticket, gone.id, staff_headers).status_code == 422


def test_cannot_assign_to_nonexistent_user(client, make_user, make_ticket, staff_headers):
    ticket = make_ticket(make_user())

    assert put_assignee(client, ticket, 999999, staff_headers).status_code == 422


def test_requester_cannot_assign_own_ticket(client, make_user, make_ticket, auth):
    me = make_user()
    tech = make_user(role=Role.TECHNICIAN)
    ticket = make_ticket(me)

    assert put_assignee(client, ticket, tech.id, auth(me)).status_code == 403


def test_requester_gets_403_assigning_others_ticket(client, make_user, make_ticket, auth):
    ticket = make_ticket(make_user())
    tech = make_user(role=Role.TECHNICIAN)

    assert put_assignee(client, ticket, tech.id, auth(make_user())).status_code == 403


def test_assignee_update_requires_login(client, make_user, make_ticket):
    ticket = make_ticket(make_user())

    assert put_assignee(client, ticket, None, {}).status_code == 401


def test_assignee_cannot_change_on_closed_ticket(client, make_user, make_ticket, staff_headers):
    tech = make_user(role=Role.TECHNICIAN)
    ticket = make_ticket(make_user(), status=S.CLOSED)

    assert put_assignee(client, ticket, tech.id, staff_headers).status_code == 409


def test_assignee_body_must_include_the_field(client, make_user, make_ticket, staff_headers):
    ticket = make_ticket(make_user())

    response = client.put(f"/tickets/{ticket.id}/assignee", json={}, headers=staff_headers)

    assert response.status_code == 422


def test_assignee_update_unknown_ticket_is_404(client, staff_headers):
    response = client.put(
        "/tickets/999999/assignee", json={"assignee_id": None}, headers=staff_headers
    )

    assert response.status_code == 404


# ---- GET /users/assignable ------------------------------------------------------------


@pytest.mark.parametrize("role", STAFF)
def test_staff_can_list_assignable_users(client, make_user, auth, role):
    me = make_user(role=role)
    tech = make_user(role=Role.TECHNICIAN)
    make_user()  # requester: not assignable
    make_user(role=Role.TECHNICIAN, is_active=False)  # inactive: not assignable

    response = client.get("/users/assignable", headers=auth(me))

    assert response.status_code == 200
    assert {u["id"] for u in response.json()} == {me.id, tech.id}


def test_requester_cannot_list_assignable_users(client, make_user, auth):
    assert client.get("/users/assignable", headers=auth(make_user())).status_code == 403


def test_assignable_requires_login(client):
    assert client.get("/users/assignable").status_code == 401
