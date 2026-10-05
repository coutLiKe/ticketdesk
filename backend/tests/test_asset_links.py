import pytest

from app.models import Role, TicketStatus

STAFF = [Role.TECHNICIAN, Role.ADMIN]


@pytest.fixture
def staff_headers(make_user, auth):
    return auth(make_user(role=Role.TECHNICIAN))


def link(client, ticket, asset, headers):
    return client.put(f"/tickets/{ticket.id}/assets/{asset.id}", headers=headers)


def unlink(client, ticket, asset, headers):
    return client.delete(f"/tickets/{ticket.id}/assets/{asset.id}", headers=headers)


# ---- PUT /tickets/{ticket_id}/assets/{asset_id} --------------------------------------


@pytest.mark.parametrize("role", STAFF)
def test_staff_can_link_an_asset_to_a_ticket(
    client, make_user, make_ticket, make_asset, auth, role
):
    ticket, asset = make_ticket(make_user()), make_asset()

    response = link(client, ticket, asset, auth(make_user(role=role)))

    assert response.status_code == 200
    assert [a["id"] for a in response.json()] == [asset.id]


def test_linking_is_idempotent(client, make_user, make_ticket, make_asset, staff_headers):
    ticket, asset = make_ticket(make_user()), make_asset()

    link(client, ticket, asset, staff_headers)
    response = link(client, ticket, asset, staff_headers)

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_one_ticket_can_link_several_assets(
    client, make_user, make_ticket, make_asset, staff_headers
):
    ticket = make_ticket(make_user())
    a, b = make_asset(), make_asset()

    link(client, ticket, a, staff_headers)
    response = link(client, ticket, b, staff_headers)

    assert {x["id"] for x in response.json()} == {a.id, b.id}


def test_requester_cannot_link_assets(client, make_user, make_ticket, make_asset, auth):
    me = make_user()
    ticket, asset = make_ticket(me), make_asset(assigned_to=me)

    assert link(client, ticket, asset, auth(me)).status_code == 403


def test_link_requires_login(client, make_user, make_ticket, make_asset):
    assert link(client, make_ticket(make_user()), make_asset(), {}).status_code == 401


def test_link_unknown_ticket_or_asset_is_404(
    client, make_user, make_ticket, make_asset, staff_headers
):
    ticket, asset = make_ticket(make_user()), make_asset()

    assert (
        client.put(f"/tickets/999999/assets/{asset.id}", headers=staff_headers).status_code == 404
    )
    assert (
        client.put(f"/tickets/{ticket.id}/assets/999999", headers=staff_headers).status_code == 404
    )


def test_cannot_link_to_a_closed_ticket(client, make_user, make_ticket, make_asset, staff_headers):
    ticket = make_ticket(make_user(), status=TicketStatus.CLOSED)

    assert link(client, ticket, make_asset(), staff_headers).status_code == 409


# ---- DELETE /tickets/{ticket_id}/assets/{asset_id} -----------------------------------


@pytest.mark.parametrize("role", STAFF)
def test_staff_can_unlink_an_asset(client, make_user, make_ticket, make_asset, auth, role):
    ticket, asset = make_ticket(make_user()), make_asset()
    staff = auth(make_user(role=role))
    link(client, ticket, asset, staff)

    assert unlink(client, ticket, asset, staff).status_code == 204
    assert client.get(f"/tickets/{ticket.id}/assets", headers=staff).json() == []


def test_unlinking_something_not_linked_is_404(
    client, make_user, make_ticket, make_asset, staff_headers
):
    assert unlink(client, make_ticket(make_user()), make_asset(), staff_headers).status_code == 404


def test_requester_cannot_unlink_assets(
    client, make_user, make_ticket, make_asset, staff_headers, auth
):
    me = make_user()
    ticket, asset = make_ticket(me), make_asset(assigned_to=me)
    link(client, ticket, asset, staff_headers)

    assert unlink(client, ticket, asset, auth(me)).status_code == 403


def test_unlink_requires_login(client, make_user, make_ticket, make_asset):
    assert unlink(client, make_ticket(make_user()), make_asset(), {}).status_code == 401


def test_cannot_unlink_from_a_closed_ticket(
    client, make_user, make_ticket, make_asset, staff_headers
):
    ticket, asset = make_ticket(make_user()), make_asset()
    link(client, ticket, asset, staff_headers)
    ticket.status = TicketStatus.CLOSED

    assert unlink(client, ticket, asset, staff_headers).status_code == 409


# ---- GET /tickets/{ticket_id}/assets -------------------------------------------------


def test_staff_see_every_asset_linked_to_a_ticket(
    client, make_user, make_ticket, make_asset, staff_headers
):
    ticket = make_ticket(make_user())
    a, b = make_asset(), make_asset(assigned_to=make_user())
    link(client, ticket, a, staff_headers)
    link(client, ticket, b, staff_headers)

    response = client.get(f"/tickets/{ticket.id}/assets", headers=staff_headers)

    assert {x["id"] for x in response.json()} == {a.id, b.id}


def test_requester_sees_only_linked_assets_assigned_to_themselves(
    client, make_user, make_ticket, make_asset, staff_headers, auth
):
    """A shared device linked to my ticket shouldn't expose someone else's equipment."""
    me = make_user()
    ticket = make_ticket(me)
    mine = make_asset(assigned_to=me)
    theirs = make_asset(assigned_to=make_user())
    stock = make_asset()
    for asset in (mine, theirs, stock):
        link(client, ticket, asset, staff_headers)

    response = client.get(f"/tickets/{ticket.id}/assets", headers=auth(me))

    assert [x["id"] for x in response.json()] == [mine.id]


def test_requester_cannot_list_assets_of_someone_elses_ticket(client, make_user, make_ticket, auth):
    ticket = make_ticket(make_user())

    assert client.get(f"/tickets/{ticket.id}/assets", headers=auth(make_user())).status_code == 404


def test_ticket_assets_requires_login(client, make_user, make_ticket):
    assert client.get(f"/tickets/{make_ticket(make_user()).id}/assets").status_code == 401


def test_ticket_assets_unknown_ticket_is_404(client, staff_headers):
    assert client.get("/tickets/999999/assets", headers=staff_headers).status_code == 404


# ---- GET /assets/{asset_id}/tickets --------------------------------------------------


def test_staff_see_all_tickets_linked_to_an_asset(
    client, make_user, make_ticket, make_asset, staff_headers
):
    asset = make_asset()
    t1, t2 = make_ticket(make_user()), make_ticket(make_user())
    make_ticket(make_user())  # not linked
    link(client, t1, asset, staff_headers)
    link(client, t2, asset, staff_headers)

    response = client.get(f"/assets/{asset.id}/tickets", headers=staff_headers)

    assert {t["id"] for t in response.json()} == {t1.id, t2.id}


def test_requester_sees_only_their_own_tickets_for_their_asset(
    client, make_user, make_ticket, make_asset, staff_headers, auth
):
    me, other = make_user(), make_user()
    asset = make_asset(assigned_to=me)
    mine, theirs = make_ticket(me), make_ticket(other)
    link(client, mine, asset, staff_headers)
    link(client, theirs, asset, staff_headers)

    response = client.get(f"/assets/{asset.id}/tickets", headers=auth(me))

    assert [t["id"] for t in response.json()] == [mine.id]


def test_requester_cannot_list_tickets_of_an_asset_that_is_not_theirs(
    client, make_user, make_asset, auth
):
    assert (
        client.get(f"/assets/{make_asset().id}/tickets", headers=auth(make_user())).status_code
        == 404
    )


def test_asset_tickets_requires_login(client, make_asset):
    assert client.get(f"/assets/{make_asset().id}/tickets").status_code == 401


def test_asset_tickets_unknown_asset_is_404(client, staff_headers):
    assert client.get("/assets/999999/tickets", headers=staff_headers).status_code == 404
