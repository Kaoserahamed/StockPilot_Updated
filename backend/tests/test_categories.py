"""Category management (FR-4): create, update, deactivate and delete guards."""

from fastapi.testclient import TestClient

from tests import factories

CATEGORIES = "/api/v1/categories"


def test_create_and_list_categories(client: TestClient) -> None:
    headers = factories.register_owner(client, email="cat1@test.com")

    created = client.post(CATEGORIES, json={"name": "Grocery", "description": "Food"}, headers=headers)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["name"] == "Grocery"
    assert body["is_active"] is True

    listed = client.get(CATEGORIES, headers=headers)
    assert listed.status_code == 200
    assert [c["name"] for c in listed.json()] == ["Grocery"]


def test_duplicate_category_name_is_rejected(client: TestClient) -> None:
    headers = factories.register_owner(client, email="cat2@test.com")
    factories.create_category(client, headers, name="Grocery")

    resp = client.post(CATEGORIES, json={"name": "Grocery"}, headers=headers)
    assert resp.status_code == 409


def test_same_name_is_allowed_in_a_different_business(client: TestClient) -> None:
    """Uniqueness is scoped per business, not global."""
    first = factories.register_owner(client, email="cat3@test.com")
    second = factories.register_owner(client, email="cat4@test.com")

    factories.create_category(client, first, name="Grocery")
    other = client.post(CATEGORIES, json={"name": "Grocery"}, headers=second)
    assert other.status_code == 201


def test_update_category(client: TestClient) -> None:
    headers = factories.register_owner(client, email="cat5@test.com")
    category = factories.create_category(client, headers, name="Grocery")

    resp = client.patch(f"{CATEGORIES}/{category['id']}", json={"name": "Groceries"}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Groceries"


def test_deactivate_category(client: TestClient) -> None:
    headers = factories.register_owner(client, email="cat6@test.com")
    category = factories.create_category(client, headers)

    resp = client.post(f"{CATEGORIES}/{category['id']}/deactivate", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_active"] is False


def test_delete_is_blocked_while_products_reference_the_category(client: TestClient) -> None:
    """FR-4.4: a category in use must be reassigned before deletion."""
    headers = factories.register_owner(client, email="cat7@test.com")
    category = factories.create_category(client, headers)
    factories.create_product(client, headers, category_id=category["id"])

    resp = client.delete(f"{CATEGORIES}/{category['id']}", headers=headers)
    assert resp.status_code == 400, resp.text
    assert "Reassign" in resp.json()["detail"]


def test_delete_succeeds_once_the_category_is_unused(client: TestClient) -> None:
    headers = factories.register_owner(client, email="cat8@test.com")
    category = factories.create_category(client, headers)

    resp = client.delete(f"{CATEGORIES}/{category['id']}", headers=headers)
    assert resp.status_code == 200, resp.text
    assert client.get(CATEGORIES, headers=headers).json() == []


def test_unknown_category_returns_not_found(client: TestClient) -> None:
    headers = factories.register_owner(client, email="cat9@test.com")
    assert client.delete(f"{CATEGORIES}/999999", headers=headers).status_code == 404
    assert (
        client.patch(f"{CATEGORIES}/999999", json={"name": "x"}, headers=headers).status_code == 404
    )


def test_categories_are_not_visible_across_businesses(client: TestClient) -> None:
    first = factories.register_owner(client, email="cat10@test.com")
    second = factories.register_owner(client, email="cat11@test.com")
    factories.create_category(client, first, name="Private")

    assert client.get(CATEGORIES, headers=second).json() == []
    assert client.delete(f"{CATEGORIES}/1", headers=second).status_code == 404


def test_category_writes_require_an_authorised_role(client: TestClient) -> None:
    headers = factories.register_owner(client, email="cat12@test.com")
    cashier = factories.create_cashier(client, headers, email="cat-cashier@test.com")

    assert client.post(CATEGORIES, json={"name": "Nope"}, headers=cashier).status_code == 403


def test_category_writes_require_authentication(client: TestClient) -> None:
    assert client.get(CATEGORIES).status_code == 401
    assert client.post(CATEGORIES, json={"name": "Anon"}).status_code == 401
