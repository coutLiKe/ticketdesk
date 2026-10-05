"""Spec for M4 (ticket comments). See docs/M4-comments-spec.md."""

import pytest
from sqlalchemy import func, select

from app.models import Comment, Role, TicketStatus

STAFF = [Role.TECHNICIAN, Role.ADMIN]


def post(client, ticket, headers, **body):
    body.setdefault("body", "Have you tried turning it off and on again?")
    return client.post(f"/tickets/{ticket.id}/comments", json=body, headers=headers)


def get(client, ticket, headers):
    return client.get(f"/tickets/{ticket.id}/comments", headers=headers)


def comment_count(db) -> int:
    return db.scalar(select(func.count(Comment.id)))


# ======================================================================================
# POST /tickets/{ticket_id}/comments
# ======================================================================================


def test_requester_can_comment_on_own_ticket(client, make_user, make_ticket, auth):
    me = make_user()
    ticket = make_ticket(me)

    response = post(client, ticket, auth(me), body="Still broken")

    assert response.status_code == 201
    body = response.json()
    assert body["body"] == "Still broken"
    assert body["ticket_id"] == ticket.id
    assert body["is_internal"] is False
    assert body["author"]["id"] == me.id
    assert "email" not in body["author"]


@pytest.mark.parametrize("role", STAFF)
def test_staff_can_comment_on_any_ticket(client, make_user, make_ticket, auth, role):
    ticket = make_ticket(make_user())
    staff = make_user(role=role)

    response = post(client, ticket, auth(staff))

    assert response.status_code == 201
    assert response.json()["author"]["id"] == staff.id


def test_requester_cannot_comment_on_someone_elses_ticket(client, make_user, make_ticket, auth, db):
    ticket = make_ticket(make_user())

    response = post(client, ticket, auth(make_user()))

    assert response.status_code == 404
    assert comment_count(db) == 0


def test_comment_requires_login(client, make_user, make_ticket):
    ticket = make_ticket(make_user())

    assert post(client, ticket, {}).status_code == 401


def test_comment_on_unknown_ticket_is_404(client, make_user, auth):
    response = client.post(
        "/tickets/999999/comments", json={"body": "hi"}, headers=auth(make_user())
    )

    assert response.status_code == 404


def test_comment_is_stored_in_the_database(client, make_user, make_ticket, auth, db):
    me = make_user()
    ticket = make_ticket(me)

    post(client, ticket, auth(me), body="Persisted?")

    stored = db.scalars(select(Comment)).one()
    assert (stored.ticket_id, stored.author_id, stored.body) == (ticket.id, me.id, "Persisted?")


def test_author_comes_from_the_token_not_the_request_body(client, make_user, make_ticket, auth):
    me, other = make_user(), make_user()
    ticket = make_ticket(me)

    response = post(client, ticket, auth(me), author_id=other.id)

    assert response.json()["author"]["id"] == me.id


def test_body_is_trimmed(client, make_user, make_ticket, auth):
    me = make_user()
    ticket = make_ticket(me)

    assert post(client, ticket, auth(me), body="  padded  ").json()["body"] == "padded"


@pytest.mark.parametrize("body", ["", "   ", "x" * 5001])
def test_invalid_body_is_422(client, make_user, make_ticket, auth, db, body):
    me = make_user()
    ticket = make_ticket(me)

    assert post(client, ticket, auth(me), body=body).status_code == 422
    assert comment_count(db) == 0


def test_missing_body_is_422(client, make_user, make_ticket, auth):
    me = make_user()
    ticket = make_ticket(me)

    response = client.post(f"/tickets/{ticket.id}/comments", json={}, headers=auth(me))

    assert response.status_code == 422


def test_is_internal_must_be_a_boolean(client, make_user, make_ticket, auth):
    tech = make_user(role=Role.TECHNICIAN)
    ticket = make_ticket(make_user())

    assert post(client, ticket, auth(tech), is_internal="maybe").status_code == 422


@pytest.mark.parametrize(
    "status", [TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED]
)
def test_can_comment_while_ticket_is_not_closed(client, make_user, make_ticket, auth, status):
    me = make_user()
    ticket = make_ticket(me, status=status)

    assert post(client, ticket, auth(me)).status_code == 201


@pytest.mark.parametrize("role", [Role.REQUESTER, *STAFF])
def test_cannot_comment_on_a_closed_ticket(client, make_user, make_ticket, auth, db, role):
    requester = make_user()
    ticket = make_ticket(requester, status=TicketStatus.CLOSED)
    commenter = requester if role == Role.REQUESTER else make_user(role=role)

    assert post(client, ticket, auth(commenter)).status_code == 409
    assert comment_count(db) == 0


# ---- internal notes (POST) -----------------------------------------------------------


@pytest.mark.parametrize("role", STAFF)
def test_staff_can_post_internal_notes(client, make_user, make_ticket, auth, role):
    ticket = make_ticket(make_user())

    response = post(client, ticket, auth(make_user(role=role)), is_internal=True)

    assert response.status_code == 201
    assert response.json()["is_internal"] is True


def test_requester_cannot_post_internal_notes(client, make_user, make_ticket, auth, db):
    me = make_user()
    ticket = make_ticket(me)

    response = post(client, ticket, auth(me), is_internal=True)

    assert response.status_code == 403
    assert comment_count(db) == 0


def test_requester_can_send_is_internal_false_explicitly(client, make_user, make_ticket, auth):
    me = make_user()
    ticket = make_ticket(me)

    assert post(client, ticket, auth(me), is_internal=False).status_code == 201


# ======================================================================================
# GET /tickets/{ticket_id}/comments
# ======================================================================================


def test_list_is_empty_for_a_ticket_without_comments(client, make_user, make_ticket, auth):
    me = make_user()
    ticket = make_ticket(me)

    response = get(client, ticket, auth(me))

    assert response.status_code == 200
    assert response.json() == []


def test_comments_are_listed_oldest_first(client, make_user, make_ticket, make_comment, auth):
    me = make_user()
    ticket = make_ticket(me)
    make_comment(ticket, me, body="first")
    make_comment(ticket, me, body="second")
    make_comment(ticket, me, body="third")

    response = get(client, ticket, auth(me))

    assert [c["body"] for c in response.json()] == ["first", "second", "third"]


def test_only_comments_from_the_requested_ticket_are_returned(
    client, make_user, make_ticket, make_comment, auth
):
    me = make_user()
    mine, other = make_ticket(me), make_ticket(me)
    make_comment(mine, me, body="on mine")
    make_comment(other, me, body="on other")

    assert [c["body"] for c in get(client, mine, auth(me)).json()] == ["on mine"]


def test_listed_comment_has_the_expected_shape(client, make_user, make_ticket, make_comment, auth):
    me = make_user()
    ticket = make_ticket(me)
    make_comment(ticket, me)

    item = get(client, ticket, auth(me)).json()[0]

    assert set(item) == {"id", "ticket_id", "author", "body", "is_internal", "created_at"}
    assert set(item["author"]) == {"id", "full_name", "role"}


def test_requester_cannot_list_comments_on_someone_elses_ticket(
    client, make_user, make_ticket, make_comment, auth
):
    owner = make_user()
    ticket = make_ticket(owner)
    make_comment(ticket, owner)

    assert get(client, ticket, auth(make_user())).status_code == 404


@pytest.mark.parametrize("role", STAFF)
def test_staff_can_list_comments_on_any_ticket(
    client, make_user, make_ticket, make_comment, auth, role
):
    owner = make_user()
    ticket = make_ticket(owner)
    make_comment(ticket, owner)

    response = get(client, ticket, auth(make_user(role=role)))

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_list_requires_login(client, make_user, make_ticket):
    assert get(client, make_ticket(make_user()), {}).status_code == 401


def test_list_for_unknown_ticket_is_404(client, make_user, auth):
    assert client.get("/tickets/999999/comments", headers=auth(make_user())).status_code == 404


def test_can_read_comments_on_a_closed_ticket(client, make_user, make_ticket, make_comment, auth):
    me = make_user()
    ticket = make_ticket(me, status=TicketStatus.CLOSED)
    make_comment(ticket, me)

    assert len(get(client, ticket, auth(me)).json()) == 1


# ---- internal notes (GET) ------------------------------------------------------------


def test_requester_never_sees_internal_notes(client, make_user, make_ticket, make_comment, auth):
    me = make_user()
    tech = make_user(role=Role.TECHNICIAN)
    ticket = make_ticket(me)
    make_comment(ticket, me, body="public from requester")
    make_comment(ticket, tech, body="public from tech")
    make_comment(ticket, tech, body="SECRET internal note", is_internal=True)

    response = get(client, ticket, auth(me))

    bodies = [c["body"] for c in response.json()]
    assert bodies == ["public from requester", "public from tech"]
    assert "SECRET" not in response.text


@pytest.mark.parametrize("role", STAFF)
def test_staff_see_internal_notes_too(client, make_user, make_ticket, make_comment, auth, role):
    me = make_user()
    tech = make_user(role=Role.TECHNICIAN)
    ticket = make_ticket(me)
    make_comment(ticket, me, body="public")
    make_comment(ticket, tech, body="internal", is_internal=True)

    response = get(client, ticket, auth(make_user(role=role)))

    assert [(c["body"], c["is_internal"]) for c in response.json()] == [
        ("public", False),
        ("internal", True),
    ]


def test_internal_note_posted_by_staff_is_hidden_from_requester_end_to_end(
    client, make_user, make_ticket, auth
):
    me = make_user()
    tech = make_user(role=Role.TECHNICIAN)
    ticket = make_ticket(me)

    post(client, ticket, auth(tech), body="Looks like a bad cable", is_internal=True)
    post(client, ticket, auth(tech), body="We are looking into it")

    requester_view = get(client, ticket, auth(me)).json()
    staff_view = get(client, ticket, auth(tech)).json()

    assert [c["body"] for c in requester_view] == ["We are looking into it"]
    assert len(staff_view) == 2


def test_requester_still_sees_only_public_notes_on_a_closed_ticket(
    client, make_user, make_ticket, make_comment, auth
):
    me = make_user()
    tech = make_user(role=Role.TECHNICIAN)
    ticket = make_ticket(me, status=TicketStatus.CLOSED)
    make_comment(ticket, tech, body="internal", is_internal=True)

    assert get(client, ticket, auth(me)).json() == []
