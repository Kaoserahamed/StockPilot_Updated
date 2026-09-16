"""Business profile management (FR-2) and tenant scoping of the profile itself."""

from fastapi.testclient import TestClient

from tests import factories

BUSINESSES = "/api/v1/businesses"


def test_owner_can_read_their_business_profile(client: TestClient) -> None:
    headers = factories.register_owner(client, email="biz1@test.com", business_name="Corner Store")
    resp = client.get(f"{BUSINESSES}/me", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Corner Store"
    assert body["currency"] == "BDT"  # documented default


def test_owner_can_update_the_business_profile(client: TestClient) -> None:
    headers = factories.register_owner(client, email="biz2@test.com")
    resp = client.patch(
        f"{BUSINESSES}/me",
        json={"name": "Renamed Shop", "address": "12 Main Street", "phone": "01700000000"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["name"] == "Renamed Shop"
    assert body["address"] == "12 Main Street"
    assert body["phone"] == "01700000000"


def test_owner_can_create_an_additional_business(client: TestClient) -> None:
    """FR-2.1/FR-24: one owner may hold memberships in several businesses."""
    headers = factories.register_owner(client, email="biz3@test.com")

    created = client.post(
        f"{BUSINESSES}", json={"name": "Second Branch", "currency": "USD"}, headers=headers
    )
    assert created.status_code == 201, created.text
    second_id = created.json()["id"]

    # the new business is reachable by selecting it explicitly
    scoped = client.get(f"{BUSINESSES}/me", headers={**headers, "X-Business-Id": str(second_id)})
    assert scoped.status_code == 200
    assert scoped.json()["name"] == "Second Branch"

    # and data stays scoped to the selected business
    client.post(
        "/api/v1/products",
        json={"name": "Only In Branch", "sku": "BR-1"},
        headers={**headers, "X-Business-Id": str(second_id)},
    )
    in_branch = client.get(
        "/api/v1/products", headers={**headers, "X-Business-Id": str(second_id)}
    ).json()
    in_original = client.get("/api/v1/products", headers=headers).json()
    assert [p["name"] for p in in_branch] == ["Only In Branch"]
    assert in_original == []


def test_cannot_select_a_business_you_do_not_belong_to(client: TestClient) -> None:
    first = factories.register_owner(client, email="biz4@test.com")
    factories.register_owner(client, email="biz5@test.com")

    resp = client.get(f"{BUSINESSES}/me", headers={**first, "X-Business-Id": "999999"})
    assert resp.status_code == 403


def test_manager_cannot_rename_the_business(client: TestClient) -> None:
    headers = factories.register_owner(client, email="biz6@test.com")
    manager = factories.create_employee(
        client, headers, name="Manager", email="biz-manager@test.com", role="Manager"
    )
    manager_headers = factories.login(client, "biz-manager@test.com")

    assert manager["role"] == "Manager"
    assert (
        client.patch(
            f"{BUSINESSES}/me", json={"name": "Hijacked"}, headers=manager_headers
        ).status_code
        == 403
    )
    assert (
        client.post(f"{BUSINESSES}", json={"name": "Mine"}, headers=manager_headers).status_code
        == 403
    )


def test_owner_can_upload_a_logo(client: TestClient) -> None:
    """FR-2.2: logo is stored on the local filesystem and the path is persisted."""
    headers = factories.register_owner(client, email="biz7@test.com")

    resp = client.post(
        f"{BUSINESSES}/me/logo",
        files={"file": ("logo.png", b"\x89PNG\r\n\x1a\n fake image bytes", "image/png")},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["logo_path"]


def test_business_endpoints_require_authentication(client: TestClient) -> None:
    assert client.get(f"{BUSINESSES}/me").status_code == 401
    assert client.patch(f"{BUSINESSES}/me", json={"name": "Anon"}).status_code == 401
