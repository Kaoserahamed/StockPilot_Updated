"""Purchasing (FR-10): multi-item receipts, payment schedule and cancellation."""

from fastapi.testclient import TestClient

from tests import factories

API = "/api/v1"


def _items(shop, qty=4, cost=60):
    return [{"product_id": shop.product_id, "quantity": qty, "unit_cost": cost}]


def test_purchase_receives_stock_and_totals_are_computed(client: TestClient, shop) -> None:
    before = shop.qty(client)
    purchase = factories.create_purchase(
        client,
        shop.headers,
        shop.supplier_id,
        _items(shop),
        discount_amount=10,
        tax_amount=5,
    )
    assert purchase["subtotal"] == 240
    assert purchase["total_amount"] == 235
    assert purchase["status"] == "confirmed"
    assert shop.qty(client) == before + 4


def test_unpaid_purchase_is_flagged_and_supplier_owes_balance(client: TestClient, shop) -> None:
    purchase = factories.create_purchase(client, shop.headers, shop.supplier_id, _items(shop))
    assert purchase["payment_status"] == "unpaid"

    suppliers = client.get(f"{API}/suppliers", headers=shop.headers).json()
    mine = next(s for s in suppliers if s["id"] == shop.supplier_id)
    assert mine["outstanding_balance"] >= purchase["total_amount"]


def test_partial_payment_then_full_payment_transitions_status(client: TestClient, shop) -> None:
    purchase = factories.create_purchase(
        client, shop.headers, shop.supplier_id, _items(shop, qty=10, cost=100)
    )
    total = purchase["total_amount"]

    part = client.post(
        f"{API}/purchases/{purchase['id']}/pay",
        json={"amount": 200},
        headers=shop.headers,
    )
    assert part.status_code == 200, part.text
    assert part.json()["payment_status"] == "partial"

    rest = client.post(
        f"{API}/purchases/{purchase['id']}/pay",
        json={"amount": total - 200},
        headers=shop.headers,
    )
    assert rest.status_code == 200, rest.text
    assert rest.json()["payment_status"] == "paid"


def test_overpayment_is_rejected(client: TestClient, shop) -> None:
    purchase = factories.create_purchase(client, shop.headers, shop.supplier_id, _items(shop))
    resp = client.post(
        f"{API}/purchases/{purchase['id']}/pay",
        json={"amount": purchase["total_amount"] + 1},
        headers=shop.headers,
    )
    assert resp.status_code == 422


def test_purchase_list_and_detail_round_trip(client: TestClient, shop) -> None:
    purchase = factories.create_purchase(client, shop.headers, shop.supplier_id, _items(shop))
    listing = client.get(f"{API}/purchases", headers=shop.headers).json()
    assert any(p["id"] == purchase["id"] for p in listing)

    detail = client.get(f"{API}/purchases/{purchase['id']}", headers=shop.headers).json()
    assert detail["supplier_name"]
    assert len(detail["items"]) == 1


def test_cancel_reverses_stock_and_marks_status(client: TestClient, shop) -> None:
    before = shop.qty(client)
    purchase = factories.create_purchase(
        client, shop.headers, shop.supplier_id, _items(shop, qty=3)
    )
    assert shop.qty(client) == before + 3

    cancelled = client.post(f"{API}/purchases/{purchase['id']}/cancel", headers=shop.headers)
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"
    assert shop.qty(client) == before

    # paying a cancelled purchase is a no-op guard, not a crash
    assert (
        client.post(
            f"{API}/purchases/{purchase['id']}/pay",
            json={"amount": 10},
            headers=shop.headers,
        ).status_code
        == 400
    )


def test_purchase_validates_supplier_product_and_amounts(client: TestClient, shop) -> None:
    bad_supplier = client.post(
        f"{API}/purchases",
        json={"supplier_id": 999999, "items": _items(shop)},
        headers=shop.headers,
    )
    assert bad_supplier.status_code == 400

    bad_product = client.post(
        f"{API}/purchases",
        json={
            "supplier_id": shop.supplier_id,
            "items": [{"product_id": 999999, "quantity": 1, "unit_cost": 1}],
        },
        headers=shop.headers,
    )
    assert bad_product.status_code == 400

    negative = client.post(
        f"{API}/purchases",
        json={
            "supplier_id": shop.supplier_id,
            "items": _items(shop),
            "discount_amount": 100000,
        },
        headers=shop.headers,
    )
    assert negative.status_code == 422


def test_cashier_cannot_create_or_pay_purchases(client: TestClient, shop) -> None:
    cashier = factories.create_cashier(client, shop.headers, email="pur-c@test.com")
    purchase = factories.create_purchase(client, shop.headers, shop.supplier_id, _items(shop))

    create = client.post(
        f"{API}/purchases",
        json={"supplier_id": shop.supplier_id, "items": _items(shop)},
        headers=cashier,
    )
    pay = client.post(f"{API}/purchases/{purchase['id']}/pay", json={"amount": 10}, headers=cashier)
    assert create.status_code == 403
    assert pay.status_code == 403
