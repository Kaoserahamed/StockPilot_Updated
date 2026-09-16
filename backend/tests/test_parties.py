"""Suppliers and customers (FR-6, FR-7): CRUD, histories and balances."""

from fastapi.testclient import TestClient

from tests import factories


# --------------------------------------------------------------------------- #
# Suppliers
# --------------------------------------------------------------------------- #
def test_create_supplier_with_contact_details(client: TestClient) -> None:
    headers = factories.register_owner(client, email="sup1@test.com")
    resp = client.post(
        "/api/v1/suppliers",
        json={
            "company_name": "Acme Supplies",
            "contact_person": "Rahim",
            "phone": "01711111111",
            "email": "sales@acme.test",
            "address": "Industrial Area",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["company_name"] == "Acme Supplies"
    assert body["contact_person"] == "Rahim"
    assert body["outstanding_balance"] == 0
    assert body["is_active"] is True


def test_supplier_can_be_updated_and_deactivated(client: TestClient) -> None:
    headers = factories.register_owner(client, email="sup2@test.com")
    supplier = factories.create_supplier(client, headers)

    updated = client.patch(
        f"/api/v1/suppliers/{supplier['id']}", json={"company_name": "Acme Ltd"}, headers=headers
    )
    assert updated.status_code == 200
    assert updated.json()["company_name"] == "Acme Ltd"

    off = client.post(f"/api/v1/suppliers/{supplier['id']}/deactivate", headers=headers)
    assert off.status_code == 200
    assert off.json()["is_active"] is False


def test_unknown_supplier_update_returns_not_found(client: TestClient) -> None:
    headers = factories.register_owner(client, email="sup3@test.com")
    assert client.patch("/api/v1/suppliers/999999", json={"company_name": "X"}, headers=headers).status_code == 404


def test_supplier_purchase_history_and_payable_balance(client: TestClient) -> None:
    """FR-6.4/6.5: purchase history plus the outstanding payable."""
    headers = factories.register_owner(client, email="sup4@test.com")
    supplier = factories.create_supplier(client, headers)
    product = factories.create_product(client, headers)

    factories.create_purchase(
        client,
        headers,
        supplier["id"],
        [{"product_id": product["id"], "quantity": 10, "unit_cost": 50}],
        paid_amount=200,
    )

    history = client.get(f"/api/v1/suppliers/{supplier['id']}/purchases", headers=headers).json()
    assert history["supplier_id"] == supplier["id"]
    assert len(history["purchases"]) == 1
    assert history["purchases"][0]["total_amount"] == 500
    assert history["outstanding_balance"] == 300


def test_unknown_supplier_history_returns_not_found(client: TestClient) -> None:
    headers = factories.register_owner(client, email="sup5@test.com")
    assert client.get("/api/v1/suppliers/999999/purchases", headers=headers).status_code == 404


def test_suppliers_are_isolated_between_businesses(client: TestClient) -> None:
    first = factories.register_owner(client, email="sup6@test.com")
    second = factories.register_owner(client, email="sup7@test.com")
    supplier = factories.create_supplier(client, first, company_name="Mine")

    assert client.get("/api/v1/suppliers", headers=second).json() == []
    assert (
        client.get(f"/api/v1/suppliers/{supplier['id']}/purchases", headers=second).status_code
        == 404
    )
# --------------------------------------------------------------------------- #
# Customers
# --------------------------------------------------------------------------- #
def test_create_customer_with_credit_details(client: TestClient) -> None:
    headers = factories.register_owner(client, email="cus1@test.com")
    resp = client.post(
        "/api/v1/customers",
        json={
            "name": "Karim",
            "phone": "01811111111",
            "email": "karim@test.com",
            "address": "Village Road",
            "credit_limit": 5000,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Karim"
    assert body["credit_limit"] == 5000
    assert body["outstanding_balance"] == 0


def test_customer_can_be_updated(client: TestClient) -> None:
    headers = factories.register_owner(client, email="cus2@test.com")
    customer = factories.create_customer(client, headers, name="Karim")

    resp = client.patch(
        f"/api/v1/customers/{customer['id']}", json={"name": "Karim Ahmed"}, headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Karim Ahmed"


def test_unknown_customer_update_returns_not_found(client: TestClient) -> None:
    headers = factories.register_owner(client, email="cus3@test.com")
    assert (
        client.patch("/api/v1/customers/999999", json={"name": "X"}, headers=headers).status_code
        == 404
    )


def test_credit_sale_tracks_the_outstanding_balance(client: TestClient) -> None:
    """FR-7.4/7.5: a credit sale increases the customer's outstanding balance."""
    shop = factories.seed_shop(client, email="cus4@test.com")

    factories.checkout(
        client,
        shop.headers,
        [{"product_id": shop.product_id, "quantity": 2}],
        customer_id=shop.customer_id,
        payment_method="credit",
        paid_amount=0,
    )

    history = client.get(
        f"/api/v1/customers/{shop.customer_id}/sales", headers=shop.headers
    ).json()
    assert history["customer_id"] == shop.customer_id
    assert len(history["sales"]) == 1
    assert history["sales"][0]["total_amount"] == 200
    assert history["outstanding_balance"] == 200


def test_cancelling_a_credit_sale_clears_the_balance_and_restocks(client: TestClient) -> None:
    shop = factories.seed_shop(client, email="cus5@test.com")
    sale = factories.checkout(
        client,
        shop.headers,
        [{"product_id": shop.product_id, "quantity": 3}],
        customer_id=shop.customer_id,
        payment_method="credit",
        paid_amount=0,
    )
    stock_after_sale = shop.qty(client)

    cancelled = client.post(
        f"/api/v1/sales/{sale['id']}/cancel",
        json={"reason": "customer changed their mind"},
        headers=shop.headers,
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"

    balance = client.get(
        f"/api/v1/customers/{shop.customer_id}/sales", headers=shop.headers
    ).json()["outstanding_balance"]
    assert balance == 0
    assert shop.qty(client) == stock_after_sale + 3


def test_unknown_customer_history_returns_not_found(client: TestClient) -> None:
    headers = factories.register_owner(client, email="cus6@test.com")
    assert client.get("/api/v1/customers/999999/sales", headers=headers).status_code == 404


def test_cashier_may_register_customers_and_suppliers(client: TestClient) -> None:
    """Till staff must be able to add a walk-in customer mid-sale."""
    headers = factories.register_owner(client, email="cus7@test.com")
    cashier = factories.create_cashier(client, headers, email="party-cashier@test.com")

    assert (
        client.post("/api/v1/customers", json={"name": "Walk-in"}, headers=cashier).status_code
        == 201
    )
    assert (
        client.post("/api/v1/suppliers", json={"company_name": "New"}, headers=cashier).status_code
        == 201
    )


def test_parties_require_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/suppliers").status_code == 401
    assert client.get("/api/v1/customers").status_code == 401