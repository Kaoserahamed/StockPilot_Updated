"""Expenses (FR-15): creation, category guard, update and delete flow."""

from fastapi.testclient import TestClient

from tests import factories

API = "/api/v1"


def test_create_expense_normalises_category(client: TestClient, shop) -> None:
    expense = factories.create_expense(
        client, shop.headers, category="Rent", amount=500, description="March rent"
    )
    assert expense["category"] == "rent"
    assert expense["amount"] == 500
    assert expense["description"] == "March rent"


def test_unknown_category_is_rejected(client: TestClient, shop) -> None:
    resp = client.post(
        f"{API}/expenses",
        json={"category": "yacht", "amount": 100},
        headers=shop.headers,
    )
    assert resp.status_code == 422


def test_amount_must_be_positive(client: TestClient, shop) -> None:
    resp = client.post(
        f"{API}/expenses", json={"category": "rent", "amount": 0}, headers=shop.headers
    )
    assert resp.status_code == 422


def test_history_filter_update_and_delete(client: TestClient, shop) -> None:
    rent = factories.create_expense(client, shop.headers, category="rent", amount=100)
    factories.create_expense(client, shop.headers, category="salary", amount=200)

    filtered = client.get(f"{API}/expenses?category=rent", headers=shop.headers).json()
    assert any(e["id"] == rent["id"] for e in filtered)
    assert all(e["category"] == "rent" for e in filtered)

    updated = client.patch(
        f"{API}/expenses/{rent['id']}",
        json={"amount": 150, "description": "revised"},
        headers=shop.headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["amount"] == 150

    deleted = client.delete(f"{API}/expenses/{rent['id']}", headers=shop.headers)
    assert deleted.status_code == 204
    remaining = client.get(f"{API}/expenses", headers=shop.headers).json()
    assert all(e["id"] != rent["id"] for e in remaining)


def test_cashier_cannot_touch_expenses(client: TestClient, shop) -> None:
    cashier = factories.create_cashier(client, shop.headers, email="exp-c@test.com")
    assert (
        client.post(
            f"{API}/expenses",
            json={"category": "rent", "amount": 10},
            headers=cashier,
        ).status_code
        == 403
    )
    assert client.get(f"{API}/expenses", headers=cashier).status_code == 403
