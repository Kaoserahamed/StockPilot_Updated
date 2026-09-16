"""Inventory (FR-8, FR-9): overview, alerts, manual adjustments and price history."""

from fastapi.testclient import TestClient

from tests import factories

API = "/api/v1"


def test_overview_reports_condition_per_product(client: TestClient, shop) -> None:
    headers = shop.headers
    factories.create_product(client, headers, name="Low Item", sku="LOW-1", min_stock=50)

    rows = client.get(f"{API}/inventory/overview", headers=headers).json()
    by_sku = {r["sku"]: r for r in rows}
    assert by_sku["RICE-001"]["condition"] == "ok"  # 10 on hand, min 5
    assert by_sku["LOW-1"]["condition"] == "out"  # 0 on hand


def test_overview_stock_filter_and_category_filter(client: TestClient, shop) -> None:
    headers = shop.headers
    low = client.get(f"{API}/inventory/overview?stock=low", headers=headers).json()
    assert all(r["condition"] == "low" for r in low)

    category_id = shop.product["category_id"]
    if category_id:
        rows = client.get(
            f"{API}/inventory/overview?category_id={category_id}", headers=headers
        ).json()
        assert any(r["id"] == shop.product_id for r in rows)


def test_low_and_out_of_stock_alerts_are_consistent(client: TestClient, shop) -> None:
    headers = shop.headers
    low = client.get(f"{API}/inventory/low-stock", headers=headers).json()
    out = client.get(f"{API}/inventory/out-of-stock", headers=headers).json()
    assert isinstance(low, list) and isinstance(out, list)
    # seeded product has 10 >= min 5, so it appears in neither list
    assert all(r["id"] != shop.product_id for r in low + out)

    factories.adjust_stock(client, headers, shop.product_id, -7, reason="damage")
    low = client.get(f"{API}/inventory/low-stock", headers=headers).json()
    assert any(r["id"] == shop.product_id for r in low)


def test_manual_adjustment_moves_stock_and_writes_ledger(
    client: TestClient, shop
) -> None:
    headers = shop.headers
    before = shop.qty(client)

    tx = factories.adjust_stock(client, headers, shop.product_id, 5, reason="recount")
    assert tx["quantity_change"] == 5
    assert tx["tx_type"] == "adjustment"
    assert shop.qty(client) == before + 5

    ledger = client.get(
        f"{API}/inventory/transactions?product_id={shop.product_id}", headers=headers
    ).json()
    assert any(t["quantity_change"] == 5 and t["tx_type"] == "adjustment" for t in ledger)


def test_adjustment_can_drive_stock_negative_and_is_still_audited(
    client: TestClient, shop
) -> None:
    headers = shop.headers
    factories.adjust_stock(client, headers, shop.product_id, -999, reason="write-off")
    assert shop.qty(client) == shop.stock_quantity - 999

    actions = [
        log["action"]
        for log in client.get("/api/v1/audit-logs", headers=headers).json()
    ]
    assert "inventory.adjust" in actions


def test_adjustment_requires_a_reason(client: TestClient, shop) -> None:
    resp = client.post(
        f"{API}/inventory/adjust",
        json={"product_id": shop.product_id, "quantity_change": 1, "reason": ""},
        headers=shop.headers,
    )
    assert resp.status_code == 422


def test_price_adjustment_updates_both_prices_with_history(
    client: TestClient, shop
) -> None:
    headers = shop.headers
    resp = client.post(
        f"{API}/inventory/adjust-price",
        json={
            "product_id": shop.product_id,
            "new_selling_price": 120,
            "new_purchase_price": 70,
            "reason": "supplier hike",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    row = resp.json()
    assert row["old_selling_price"] == 100
    assert row["new_selling_price"] == 120

    product = client.get(f"{API}/products/{shop.product_id}", headers=headers).json()
    assert product["selling_price"] == 120
    assert product["purchase_price"] == 70

    history = client.get(
        f"{API}/inventory/price-adjustments?product_id={shop.product_id}",
        headers=headers,
    ).json()
    assert any(h["reason"] == "supplier hike" for h in history)


def test_price_adjustment_rejects_noop_and_empty_payload(
    client: TestClient, shop
) -> None:
    headers = shop.headers
    same = client.post(
        f"{API}/inventory/adjust-price",
        json={
            "product_id": shop.product_id,
            "new_selling_price": 100,
            "new_purchase_price": 60,
            "reason": "noop",
        },
        headers=headers,
    )
    assert same.status_code == 422

    empty = client.post(
        f"{API}/inventory/adjust-price",
        json={"product_id": shop.product_id, "reason": "nothing"},
        headers=headers,
    )
    assert empty.status_code == 422


def test_cashier_cannot_adjust_stock_or_prices(client: TestClient, shop) -> None:
    cashier = factories.create_cashier(client, shop.headers, email="inv-c@test.com")
    adjust = client.post(
        f"{API}/inventory/adjust",
        json={"product_id": shop.product_id, "quantity_change": 1, "reason": "x"},
        headers=cashier,
    )
    price = client.post(
        f"{API}/inventory/adjust-price",
        json={
            "product_id": shop.product_id,
            "new_selling_price": 5,
            "reason": "x",
        },
        headers=cashier,
    )
    assert adjust.status_code == 403
    assert price.status_code == 403
