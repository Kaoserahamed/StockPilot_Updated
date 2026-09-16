"""Happy-path walkthrough mirroring ProjectDetails.md: register to AI summary.

Exercises the full money loop in one hermetic test: catalogue -> suppliers ->
purchase -> inventory -> POS -> invoice -> returns -> finance -> dashboard ->
reports -> AI. If this passes, a fresh shop can trade end to end.
"""

from fastapi.testclient import TestClient

from tests import factories

API = "/api/v1"


def test_full_shop_lifecycle(client: TestClient) -> None:
    headers = factories.register_owner(client, email="e2e@test.com", business_name="E2E Mart")

    category = factories.create_category(client, headers, name="Grocery")
    product = factories.create_product(
        client,
        headers,
        name="Rice 5kg",
        sku="E2E-RICE",
        category_id=category["id"],
        selling_price=500,
        purchase_price=400,
        min_stock=5,
    )
    supplier = factories.create_supplier(client, headers, company_name="E2E Foods")
    customer = factories.create_customer(client, headers, name="Regular")

    purchase = factories.create_purchase(
        client,
        headers,
        supplier["id"],
        [{"product_id": product["id"], "quantity": 20, "unit_cost": 400}],
        paid_amount=4000,
    )
    assert purchase["payment_status"] == "partial"

    overview = client.get(f"{API}/inventory/overview", headers=headers).json()
    assert any(r["id"] == product["id"] and r["quantity"] == 20 for r in overview)

    sale = factories.checkout(
        client,
        headers,
        [{"product_id": product["id"], "quantity": 3}],
        customer_id=customer["id"],
        payment_method="credit",
        paid_amount=500,
    )
    assert sale["total_amount"] == 1500

    invoice = client.get(f"{API}/invoices/{sale['id']}", headers=headers)
    assert invoice.status_code == 200
    pdf = client.get(f"{API}/invoices/{sale['id']}/pdf", headers=headers)
    assert pdf.content.startswith(b"%PDF")

    detail = client.get(f"{API}/sales/{sale['id']}", headers=headers).json()
    factories.create_return(
        client,
        headers,
        sale["id"],
        [{"sale_item_id": detail["items"][0]["id"], "quantity": 1}],
        reason="torn pack",
    )

    profit = client.get(f"{API}/finance/profit?preset=all", headers=headers).json()
    assert profit["orders"] >= 1

    dashboard = client.get(f"{API}/dashboard?preset=all", headers=headers).json()
    assert dashboard["inventory"]["units"] == 18  # 20 - 3 + 1

    reports = client.get(f"{API}/reports/sales?preset=all", headers=headers)
    assert reports.status_code == 200

    chat = client.post(
        f"{API}/ai/chat", json={"question": "How are we doing?"}, headers=headers
    )
    assert chat.status_code == 200
    assert chat.json()["answer"]

    summary = client.post(
        f"{API}/ai/summarize", json={"kind": "profit", "preset": "all"}, headers=headers
    )
    assert summary.status_code == 200

    audit = client.get(f"{API}/audit-logs", headers=headers).json()
    actions = {log["action"] for log in audit}
    assert {"sale.checkout", "sale.return"}.issubset(actions)
