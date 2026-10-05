import pytest

from app.models import AssetStatus, AssetType, Role

STAFF = [Role.TECHNICIAN, Role.ADMIN]
NEW_ASSET = {"asset_tag": "lt-100", "name": "MacBook Pro 14", "type": "laptop"}


@pytest.fixture
def staff_headers(make_user, auth):
    return auth(make_user(role=Role.TECHNICIAN))


def ids(response):
    return {a["id"] for a in response.json()["items"]}


# ---- POST /assets --------------------------------------------------------------------


@pytest.mark.parametrize("role", STAFF)
def test_staff_can_create_assets(client, make_user, auth, role):
    response = client.post("/assets", json=NEW_ASSET, headers=auth(make_user(role=role)))

    assert response.status_code == 201
    body = response.json()
    assert body["asset_tag"] == "LT-100"  # normalised to upper case
    assert body["name"] == "MacBook Pro 14"
    assert body["type"] == "laptop"
    assert body["status"] == "in_stock"
    assert body["assigned_user"] is None
    assert body["serial_number"] is None


def test_create_stores_serial_number(client, staff_headers):
    payload = {**NEW_ASSET, "serial_number": "C02XYZ"}

    assert client.post("/assets", json=payload, headers=staff_headers).json()["serial_number"] == (
        "C02XYZ"
    )


def test_create_ignores_status_and_assignee_from_client(client, make_user, staff_headers):
    user = make_user()
    payload = {**NEW_ASSET, "status": "retired", "assigned_user_id": user.id}

    body = client.post("/assets", json=payload, headers=staff_headers).json()

    assert body["status"] == "in_stock"
    assert body["assigned_user"] is None


def test_requester_cannot_create_assets(client, make_user, auth):
    assert client.post("/assets", json=NEW_ASSET, headers=auth(make_user())).status_code == 403


def test_create_requires_login(client):
    assert client.post("/assets", json=NEW_ASSET).status_code == 401


def test_duplicate_asset_tag_is_409_case_insensitive(client, make_asset, staff_headers):
    make_asset(tag="LT-100")

    response = client.post(
        "/assets", json={**NEW_ASSET, "asset_tag": "lt-100"}, headers=staff_headers
    )

    assert response.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "x", "type": "laptop"},
        {"asset_tag": "A1", "type": "laptop"},
        {"asset_tag": "A1", "name": "x"},
        {"asset_tag": "A1", "name": "x", "type": "toaster"},
        {"asset_tag": "  ", "name": "x", "type": "laptop"},
        {"asset_tag": "A1", "name": "", "type": "laptop"},
        {"asset_tag": "A" * 51, "name": "x", "type": "laptop"},
    ],
)
def test_create_validates_input(client, staff_headers, payload):
    assert client.post("/assets", json=payload, headers=staff_headers).status_code == 422


# ---- GET /assets ---------------------------------------------------------------------


def test_requester_sees_only_assets_assigned_to_them(client, make_user, make_asset, auth):
    me, other = make_user(), make_user()
    mine = make_asset(assigned_to=me)
    make_asset(assigned_to=other)
    make_asset()  # in stock

    body = client.get("/assets", headers=auth(me)).json()

    assert [a["id"] for a in body["items"]] == [mine.id]
    assert body["total"] == 1


def test_requester_cannot_widen_scope_with_filters(client, make_user, make_asset, auth):
    me, other = make_user(), make_user()
    make_asset(assigned_to=other)

    response = client.get(f"/assets?assigned_user_id={other.id}", headers=auth(me))

    assert response.json()["items"] == []


@pytest.mark.parametrize("role", STAFF)
def test_staff_see_all_assets(client, make_user, make_asset, auth, role):
    make_asset()
    make_asset(assigned_to=make_user())

    assert client.get("/assets", headers=auth(make_user(role=role))).json()["total"] == 2


def test_list_requires_login(client):
    assert client.get("/assets").status_code == 401


def test_filter_by_type_status_and_assignee(client, make_user, make_asset, staff_headers):
    user = make_user()
    laptop = make_asset(type=AssetType.LAPTOP)
    monitor = make_asset(type=AssetType.MONITOR, assigned_to=user)
    retired = make_asset(status=AssetStatus.RETIRED)

    assert ids(client.get("/assets?type=laptop", headers=staff_headers)) == {laptop.id, retired.id}
    assert ids(client.get("/assets?status=assigned", headers=staff_headers)) == {monitor.id}
    assert ids(client.get("/assets?status=retired", headers=staff_headers)) == {retired.id}
    assert ids(client.get(f"/assets?assigned_user_id={user.id}", headers=staff_headers)) == {
        monitor.id
    }


def test_search_matches_tag_name_or_serial_case_insensitively(client, make_asset, staff_headers):
    by_tag = make_asset(tag="DELL-77")
    by_name = make_asset(name="Dell UltraSharp")
    by_serial = make_asset(serial_number="xdellx")
    make_asset(name="Lenovo")

    assert ids(client.get("/assets?q=DELL", headers=staff_headers)) == {
        by_tag.id,
        by_name.id,
        by_serial.id,
    }


def test_search_treats_wildcards_literally(client, make_asset, staff_headers):
    literal = make_asset(name="Spare 100% new")
    make_asset(name="Other")

    assert ids(client.get("/assets?q=100%25", headers=staff_headers)) == {literal.id}


def test_search_is_scoped_for_requesters(client, make_user, make_asset, auth):
    me = make_user()
    make_asset(name="Secret laptop", assigned_to=make_user())

    assert client.get("/assets?q=secret", headers=auth(me)).json()["items"] == []


def test_pagination(client, make_asset, staff_headers):
    created = [make_asset() for _ in range(5)]
    newest_first = [a.id for a in reversed(created)]

    page = client.get("/assets?limit=2&offset=2", headers=staff_headers).json()

    assert [a["id"] for a in page["items"]] == newest_first[2:4]
    assert page["total"] == 5 and page["limit"] == 2 and page["offset"] == 2


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "offset=-1", "type=toaster", "status=x"])
def test_list_rejects_invalid_query_params(client, staff_headers, query):
    assert client.get(f"/assets?{query}", headers=staff_headers).status_code == 422


# ---- GET /assets/{id} ----------------------------------------------------------------


def test_requester_can_view_their_own_asset(client, make_user, make_asset, auth):
    me = make_user()
    asset = make_asset(assigned_to=me)

    response = client.get(f"/assets/{asset.id}", headers=auth(me))

    assert response.status_code == 200
    assert response.json()["assigned_user"]["id"] == me.id
    assert "email" not in response.json()["assigned_user"]


def test_requester_gets_404_for_assets_that_are_not_theirs(client, make_user, make_asset, auth):
    me = make_user()

    assert client.get(f"/assets/{make_asset().id}", headers=auth(me)).status_code == 404
    other = make_asset(assigned_to=make_user())
    assert client.get(f"/assets/{other.id}", headers=auth(me)).status_code == 404


@pytest.mark.parametrize("role", STAFF)
def test_staff_can_view_any_asset(client, make_user, make_asset, auth, role):
    asset = make_asset()

    assert client.get(f"/assets/{asset.id}", headers=auth(make_user(role=role))).status_code == 200


def test_view_unknown_asset_is_404(client, staff_headers):
    assert client.get("/assets/999999", headers=staff_headers).status_code == 404


def test_view_requires_login(client, make_asset):
    assert client.get(f"/assets/{make_asset().id}").status_code == 401


# ---- PATCH /assets/{id} --------------------------------------------------------------


def test_staff_can_edit_name_type_and_serial(client, make_asset, staff_headers):
    asset = make_asset()

    response = client.patch(
        f"/assets/{asset.id}",
        json={"name": "Renamed", "type": "desktop", "serial_number": "S-1"},
        headers=staff_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["name"], body["type"], body["serial_number"]) == ("Renamed", "desktop", "S-1")
    assert body["asset_tag"] == asset.asset_tag


def test_edit_cannot_change_tag_or_status(client, make_asset, staff_headers):
    asset = make_asset(tag="KEEP-1")

    body = client.patch(
        f"/assets/{asset.id}",
        json={"name": "x", "asset_tag": "HACK", "status": "retired"},
        headers=staff_headers,
    ).json()

    assert body["asset_tag"] == "KEEP-1"
    assert body["status"] == "in_stock"


def test_requester_cannot_edit_even_their_own_asset(client, make_user, make_asset, auth):
    me = make_user()
    asset = make_asset(assigned_to=me)

    assert (
        client.patch(f"/assets/{asset.id}", json={"name": "x"}, headers=auth(me)).status_code == 403
    )


def test_edit_requires_login(client, make_asset):
    assert client.patch(f"/assets/{make_asset().id}", json={"name": "x"}).status_code == 401


def test_edit_unknown_asset_is_404(client, staff_headers):
    assert (
        client.patch("/assets/999999", json={"name": "x"}, headers=staff_headers).status_code == 404
    )


@pytest.mark.parametrize("payload", [{}, {"name": ""}, {"type": "toaster"}])
def test_edit_validates_input(client, make_asset, staff_headers, payload):
    assert (
        client.patch(f"/assets/{make_asset().id}", json=payload, headers=staff_headers).status_code
        == 422
    )


# ---- PUT /assets/{id}/assignee -------------------------------------------------------


def put_assignee(client, asset, user_id, headers):
    return client.put(f"/assets/{asset.id}/assignee", json={"user_id": user_id}, headers=headers)


@pytest.mark.parametrize("role", STAFF)
def test_staff_can_assign_an_asset_to_a_user(client, make_user, make_asset, auth, role):
    asset = make_asset()
    user = make_user()

    response = put_assignee(client, asset, user.id, auth(make_user(role=role)))

    assert response.status_code == 200
    assert response.json()["status"] == "assigned"
    assert response.json()["assigned_user"]["id"] == user.id


def test_assigned_asset_becomes_visible_to_that_requester(
    client, make_user, make_asset, staff_headers, auth
):
    user = make_user()
    asset = make_asset()
    assert client.get(f"/assets/{asset.id}", headers=auth(user)).status_code == 404

    put_assignee(client, asset, user.id, staff_headers)

    assert client.get(f"/assets/{asset.id}", headers=auth(user)).status_code == 200


def test_reassigning_moves_the_asset_to_the_new_user(client, make_user, make_asset, staff_headers):
    first, second = make_user(), make_user()
    asset = make_asset(assigned_to=first)

    body = put_assignee(client, asset, second.id, staff_headers).json()

    assert body["assigned_user"]["id"] == second.id
    assert body["status"] == "assigned"


def test_null_unassigns_and_returns_to_stock(client, make_user, make_asset, staff_headers):
    asset = make_asset(assigned_to=make_user())

    body = put_assignee(client, asset, None, staff_headers).json()

    assert body["assigned_user"] is None
    assert body["status"] == "in_stock"


def test_cannot_assign_to_inactive_or_unknown_user(client, make_user, make_asset, staff_headers):
    asset = make_asset()
    gone = make_user(is_active=False)

    assert put_assignee(client, asset, gone.id, staff_headers).status_code == 422
    assert put_assignee(client, asset, 999999, staff_headers).status_code == 422


def test_cannot_assign_a_retired_asset(client, make_user, make_asset, staff_headers):
    asset = make_asset(status=AssetStatus.RETIRED)

    assert put_assignee(client, asset, make_user().id, staff_headers).status_code == 409


def test_requester_cannot_assign_assets(client, make_user, make_asset, auth):
    me = make_user()
    asset = make_asset()

    assert put_assignee(client, asset, me.id, auth(me)).status_code == 403


def test_assign_requires_login(client, make_asset):
    assert put_assignee(client, make_asset(), None, {}).status_code == 401


def test_assign_unknown_asset_is_404(client, staff_headers):
    response = client.put("/assets/999999/assignee", json={"user_id": None}, headers=staff_headers)

    assert response.status_code == 404


def test_assign_body_must_include_user_id(client, make_asset, staff_headers):
    response = client.put(f"/assets/{make_asset().id}/assignee", json={}, headers=staff_headers)

    assert response.status_code == 422


# ---- POST /assets/{id}/retire --------------------------------------------------------


@pytest.mark.parametrize("role", STAFF)
def test_staff_can_retire_an_asset_and_it_is_unassigned(client, make_user, make_asset, auth, role):
    asset = make_asset(assigned_to=make_user())

    response = client.post(f"/assets/{asset.id}/retire", headers=auth(make_user(role=role)))

    assert response.status_code == 200
    assert response.json()["status"] == "retired"
    assert response.json()["assigned_user"] is None


def test_retiring_twice_is_409(client, make_asset, staff_headers):
    asset = make_asset(status=AssetStatus.RETIRED)

    assert client.post(f"/assets/{asset.id}/retire", headers=staff_headers).status_code == 409


def test_requester_cannot_retire_assets(client, make_user, make_asset, auth):
    me = make_user()
    asset = make_asset(assigned_to=me)

    assert client.post(f"/assets/{asset.id}/retire", headers=auth(me)).status_code == 403


def test_retire_requires_login(client, make_asset):
    assert client.post(f"/assets/{make_asset().id}/retire").status_code == 401


def test_retire_unknown_asset_is_404(client, staff_headers):
    assert client.post("/assets/999999/retire", headers=staff_headers).status_code == 404
