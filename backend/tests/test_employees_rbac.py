"""Employees, roles and tenancy isolation (FR-3, FR-24..FR-26)."""

from fastapi.testclient import TestClient

from tests import factories

API = "/api/v1"


def _owner_with_staff(client: TestClient, email="rbac@test.com"):
    headers = factories.register_owner(client, email=email)
    employee = factories.create_employee(
        client, headers, name="Maya", email=f"maya-{email}", role="Manager"
    )
    return headers, employee


def test_owner_manages_employee_lifecycle(client: TestClient) -> None:
    headers, employee = _owner_with_staff(client)
    membership = employee["membership_id"]

    listed = client.get(f"{API}/employees", headers=headers).json()
    assert any(e["membership_id"] == membership for e in listed)

    demoted = client.patch(
        f"{API}/employees/{membership}/role", json={"role": "Cashier"}, headers=headers
    )
    assert demoted.status_code == 200, demoted.text
    assert demoted.json()["role"] == "Cashier"

    reset = client.post(
        f"{API}/employees/{membership}/reset-password",
        json={"new_password": "fresh-pass-1"},
        headers=headers,
    )
    assert reset.status_code == 200, reset.text
    assert (
        client.post(
            f"{API}/auth/login",
            json={"username": employee["user"]["email"], "password": "fresh-pass-1"},
        ).status_code
        == 200
    )

    off = client.post(f"{API}/employees/{membership}/deactivate", headers=headers)
    assert off.json()["is_active"] is False
    on = client.post(f"{API}/employees/{membership}/activate", headers=headers)
    assert on.json()["is_active"] is True

    removed = client.delete(f"{API}/employees/{membership}", headers=headers)
    assert removed.status_code == 200
    assert all(
        e["membership_id"] != membership
        for e in client.get(f"{API}/employees", headers=headers).json()
    )


def test_owner_membership_cannot_be_removed(client: TestClient) -> None:
    headers, _ = _owner_with_staff(client, email="rbac2@test.com")
    owner_membership = next(
        e["membership_id"]
        for e in client.get(f"{API}/employees", headers=headers).json()
        if e["role"] == "Owner"
    )
    resp = client.delete(f"{API}/employees/{owner_membership}", headers=headers)
    assert resp.status_code == 400


def test_manager_cannot_perform_owner_only_actions(client: TestClient) -> None:
    headers, employee = _owner_with_staff(client, email="rbac3@test.com")
    manager = factories.login(client, employee["user"]["email"])

    assert (
        client.post(
            f"{API}/employees",
            json={
                "name": "X",
                "email": "x-rbac3@test.com",
                "password": "secret123",
                "role": "Cashier",
            },
            headers=manager,
        ).status_code
        == 403
    )
    assert (
        client.patch(f"{API}/settings", json={"currency": "USD"}, headers=manager).status_code
        == 403
    )


def test_businesses_are_fully_isolated_between_tenants(client: TestClient) -> None:
    first = factories.seed_shop(client, email="tenant-a@test.com", business_name="Shop A")
    second = factories.seed_shop(client, email="tenant-b@test.com", business_name="Shop B")

    # catalogue isolation
    assert all(
        p["id"] != first.product_id
        for p in client.get(f"{API}/products", headers=second.headers).json()
    )
    assert (
        client.get(f"{API}/products/{first.product_id}", headers=second.headers).status_code == 404
    )

    # sales isolation
    sale = factories.checkout(
        client, first.headers, [{"product_id": first.product_id, "quantity": 1}]
    )
    assert client.get(f"{API}/sales/{sale['id']}", headers=second.headers).status_code == 404

    # cross-tenant purchase/checkout with a foreign product id is rejected
    cross_purchase = client.post(
        f"{API}/purchases",
        json={
            "supplier_id": second.supplier_id,
            "items": [{"product_id": first.product_id, "quantity": 1, "unit_cost": 1}],
        },
        headers=second.headers,
    )
    assert cross_purchase.status_code == 400

    cross_sale = client.post(
        f"{API}/sales/checkout",
        json={"items": [{"product_id": first.product_id, "quantity": 1}]},
        headers=second.headers,
    )
    assert cross_sale.status_code == 400


def test_second_business_profile_can_be_created(client: TestClient) -> None:
    headers = factories.register_owner(client, email="multi@test.com")
    resp = client.post(f"{API}/businesses", json={"name": "Second Branch"}, headers=headers)
    assert resp.status_code == 201, resp.text
    assert resp.json()["name"] == "Second Branch"
