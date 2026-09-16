"""POS checkout and sales ledger (FR-11, FR-12, FR-13)."""

from fastapi.testclient import TestClient

from tests import factories

API = "/api/v1"


def test_full_cash_checkout_reduces_stock_and_marks_paid(client: TestClient, shop) -> None:
    before = shop.qty(client)
    sale = factories.checkout(
        client, shop.headers, [{"product_id": shop.product_id, "quantity": 2}]
    )
    assert sale["payment_status"] == "paid"
    assert sale["status"] == "completed"
    assert sale["invoice_no"]
    assert sale["items"][0]["quantity"] == 2
    assert shop.qty(client) == before - 2


def test_credit_checkout_leaves_customer_outstanding(client: TestClient, shop) -> None:
    sale = factories.checkout(
        client,
        shop.headers,
        [{"product_id": shop.product_id, "quantity": 2}],
        customer_id=shop.customer_id,
        payment_method="credit",
        paid_amount=0,
    )
    assert sale["payment_status"] == "unpaid"
    assert sale["customer_id"] == shop.customer_id

    customers = client.get(f"{API}/customers", headers=shop.headers).json()
    mine = next(c for c in customers if c["id"] == shop.customer_id)
    assert mine["outstanding_balance"] >= sale["total_amount"]


def test_tax_and_discount_shape_the_total(client: TestClient, shop) -> None:
    sale = factories.checkout(
        client,
        shop.headers,
        [{"product_id": shop.product_id, "quantity": 2}],  # 2 x 100 = 200
        discount_amount=20,
        tax_percent=10,  # 10% of (200 - 20) = 18
    )
    assert sale["subtotal"] == 200
    assert sale["tax_amount"] == 18
    assert sale["total_amount"] == 198


def test_checkout_rejects_bad_method_unknown_product_and_short_stock(
    client: TestClient, shop
) -> None:
    bad_method = client.post(
        f"{API}/sales/checkout",
        json={
            "items": [{"product_id": shop.product_id, "quantity": 1}],
            "payment_method": "crypto",
        },
        headers=shop.headers,
    )
    assert bad_method.status_code == 422

    unknown = client.post(
        f"{API}/sales/checkout",
        json={"items": [{"product_id": 999999, "quantity": 1}]},
        headers=shop.headers,
    )
    assert unknown.status_code == 400

    short = client.post(
        f"{API}/sales/checkout",
        json={"items": [{"product_id": shop.product_id, "quantity": 10_000}]},
        headers=shop.headers,
    )
    assert short.status_code == 400
    assert "Insufficient stock" in short.json()["detail"]


def test_inactive_product_is_blocked_at_checkout(client: TestClient, shop) -> None:
    client.post(f"{API}/products/{shop.product_id}/deactivate", headers=shop.headers)
    resp = client.post(
        f"{API}/sales/checkout",
        json={"items": [{"product_id": shop.product_id, "quantity": 1}]},
        headers=shop.headers,
    )
    assert resp.status_code == 400
    assert "inactive" in resp.json()["detail"].lower()


def test_pos_search_only_lists_active_matching_products(client: TestClient, shop) -> None:
    hits = client.get(f"{API}/pos/search?q=Rice", headers=shop.headers).json()
    assert any(h["id"] == shop.product_id for h in hits)

    client.post(f"{API}/products/{shop.product_id}/deactivate", headers=shop.headers)
    hidden = client.get(f"{API}/pos/search?q=Rice", headers=shop.headers).json()
    assert all(h["id"] != shop.product_id for h in hidden)


def test_sales_list_detail_and_cancel(client: TestClient, shop) -> None:
    sale = factories.checkout(
        client, shop.headers, [{"product_id": shop.product_id, "quantity": 1}]
    )
    listing = client.get(f"{API}/sales", headers=shop.headers).json()
    assert any(s["id"] == sale["id"] for s in listing)

    detail = client.get(f"{API}/sales/{sale['id']}", headers=shop.headers).json()
    assert detail["invoice_no"] == sale["invoice_no"]

    before = shop.qty(client)
    cancelled = client.post(
        f"{API}/sales/{sale['id']}/cancel",
        json={"reason": "customer changed mind"},
        headers=shop.headers,
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"
    assert shop.qty(client) == before + 1


def test_cashier_can_sell_but_cannot_cancel(client: TestClient, shop) -> None:
    cashier = factories.create_cashier(client, shop.headers, email="pos-c@test.com")
    sale = client.post(
        f"{API}/sales/checkout",
        json={"items": [{"product_id": shop.product_id, "quantity": 1}]},
        headers=cashier,
    )
    assert sale.status_code == 201

    denied = client.post(
        f"{API}/sales/{sale.json()['id']}/cancel",
        json={"reason": "nope"},
        headers=cashier,
    )
    assert denied.status_code == 403


def test_invoice_json_and_pdf_are_served(client: TestClient, shop) -> None:
    sale = factories.checkout(
        client, shop.headers, [{"product_id": shop.product_id, "quantity": 1}]
    )
    view = client.get(f"{API}/invoices/{sale['id']}", headers=shop.headers)
    assert view.status_code == 200
    assert view.json()["invoice_no"] == sale["invoice_no"]

    pdf = client.get(f"{API}/invoices/{sale['id']}/pdf", headers=shop.headers)
    assert pdf.status_code == 200
    assert "application/pdf" in pdf.headers["content-type"]
    assert pdf.content.startswith(b"%PDF")
