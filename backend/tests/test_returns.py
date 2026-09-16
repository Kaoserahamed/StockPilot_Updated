"""Returns (FR-14): partial/full refunds, stock restoration and guard rails."""

from fastapi.testclient import TestClient

from tests import factories

API = "/api/v1"


def _sale_with_items(client: TestClient, shop, qty=4):
    sale = factories.checkout(
        client, shop.headers, [{"product_id": shop.product_id, "quantity": qty}]
    )
    detail = client.get(f"{API}/sales/{sale['id']}", headers=shop.headers).json()
    return sale, detail


def test_partial_return_refunds_restocks_and_flags_sale(client: TestClient, shop) -> None:
    sale, detail = _sale_with_items(client, shop)
    before = shop.qty(client)
    item_id = detail["items"][0]["id"]

    ret = factories.create_return(
        client,
        shop.headers,
        sale["id"],
        [{"sale_item_id": item_id, "quantity": 1}],
        reason="damaged",
    )
    assert ret["refund_amount"] == 100
    assert shop.qty(client) == before + 1

    updated = client.get(f"{API}/sales/{sale['id']}", headers=shop.headers).json()
    assert updated["status"] == "partial_returned"


def test_full_return_marks_sale_returned(client: TestClient, shop) -> None:
    sale, detail = _sale_with_items(client, shop, qty=2)
    items = [{"sale_item_id": i["id"], "quantity": i["quantity"]} for i in detail["items"]]

    factories.create_return(client, shop.headers, sale["id"], items, reason="recall")
    updated = client.get(f"{API}/sales/{sale['id']}", headers=shop.headers).json()
    assert updated["status"] == "returned"


def test_return_lists_and_rejects_over_return(client: TestClient, shop) -> None:
    sale, detail = _sale_with_items(client, shop, qty=2)
    item_id = detail["items"][0]["id"]

    factories.create_return(
        client, shop.headers, sale["id"], [{"sale_item_id": item_id, "quantity": 1}]
    )
    listing = client.get(f"{API}/returns", headers=shop.headers).json()
    assert any(r["sale_id"] == sale["id"] for r in listing)

    greedy = client.post(
        f"{API}/returns",
        json={
            "sale_id": sale["id"],
            "reason": "too many",
            "items": [{"sale_item_id": item_id, "quantity": 5}],
        },
        headers=shop.headers,
    )
    assert greedy.status_code == 400
    assert "returnable" in greedy.json()["detail"]


def test_return_rejects_unknown_sale_item_and_cancelled_sale(client: TestClient, shop) -> None:
    sale, _ = _sale_with_items(client, shop)
    unknown = client.post(
        f"{API}/returns",
        json={
            "sale_id": sale["id"],
            "reason": "x",
            "items": [{"sale_item_id": 999999, "quantity": 1}],
        },
        headers=shop.headers,
    )
    assert unknown.status_code == 400

    client.post(
        f"{API}/sales/{sale['id']}/cancel",
        json={"reason": "cancel first"},
        headers=shop.headers,
    )
    late = client.post(
        f"{API}/returns",
        json={
            "sale_id": sale["id"],
            "reason": "late",
            "items": [{"sale_item_id": 1, "quantity": 1}],
        },
        headers=shop.headers,
    )
    assert late.status_code == 400


def test_cashier_cannot_accept_returns(client: TestClient, shop) -> None:
    sale, detail = _sale_with_items(client, shop, qty=1)
    cashier = factories.create_cashier(client, shop.headers, email="ret-c@test.com")
    resp = client.post(
        f"{API}/returns",
        json={
            "sale_id": sale["id"],
            "reason": "x",
            "items": [{"sale_item_id": detail["items"][0]["id"], "quantity": 1}],
        },
        headers=cashier,
    )
    assert resp.status_code == 403
