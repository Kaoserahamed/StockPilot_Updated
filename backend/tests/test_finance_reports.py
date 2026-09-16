"""Finance, dashboard, analytics and reports (FR-16..FR-23)."""

from fastapi.testclient import TestClient

from tests import factories

API = "/api/v1"


def _trading_shop(client: TestClient, email="fin@test.com"):
    shop = factories.seed_shop(client, email=email)
    factories.checkout(
        client, shop.headers, [{"product_id": shop.product_id, "quantity": 2}]
    )
    factories.create_expense(client, shop.headers, category="rent", amount=50)
    return shop


def test_revenue_cogs_and_profit_agree(client: TestClient) -> None:
    shop = _trading_shop(client)
    revenue = client.get(f"{API}/finance/revenue?preset=all", headers=shop.headers).json()
    cogs = client.get(f"{API}/finance/cogs?preset=all", headers=shop.headers).json()
    profit = client.get(f"{API}/finance/profit?preset=all", headers=shop.headers).json()

    assert revenue["gross_revenue"] == 200  # 2 x 100
    assert cogs["cogs"] == 120  # 2 x 60 average cost
    assert profit["gross_profit"] == 80
    assert profit["net_profit"] == 30  # 80 - 50 rent
    assert "trend" in revenue


def test_finance_endpoints_reject_cashiers(client: TestClient) -> None:
    shop = _trading_shop(client, email="fin2@test.com")
    cashier = factories.create_cashier(client, shop.headers, email="fin-c@test.com")
    for path in ("revenue", "cogs", "profit"):
        assert client.get(f"{API}/finance/{path}", headers=cashier).status_code == 403


def test_dashboard_bundles_kpis_trend_and_alerts(client: TestClient) -> None:
    shop = _trading_shop(client, email="dash@test.com")
    body = client.get(f"{API}/dashboard?preset=all", headers=shop.headers).json()
    assert body["orders"] >= 1
    assert body["revenue"] == 200
    assert body["net_profit"] == 30
    assert body["inventory"]["units"] >= 8  # 10 - 2 sold
    assert "sales_trend" in body and "top_products" in body


def test_product_customer_and_supplier_analytics(client: TestClient) -> None:
    shop = _trading_shop(client, email="ana@test.com")
    factories.checkout(
        client,
        shop.headers,
        [{"product_id": shop.product_id, "quantity": 1}],
        customer_id=shop.customer_id,
    )

    products = client.get(
        f"{API}/analytics/products?preset=all", headers=shop.headers
    ).json()
    assert products["best_sellers"]

    customers = client.get(
        f"{API}/analytics/customers?preset=all", headers=shop.headers
    ).json()
    assert customers["top_customers"]

    suppliers = client.get(
        f"{API}/analytics/suppliers?preset=all", headers=shop.headers
    ).json()
    assert suppliers


def test_reports_json_csv_excel_and_pdf(client: TestClient) -> None:
    shop = _trading_shop(client, email="rep@test.com")
    for kind in ("sales", "inventory", "purchases", "expenses", "profit"):
        json_body = client.get(f"{API}/reports/{kind}?preset=all", headers=shop.headers)
        assert json_body.status_code == 200, json_body.text

        csv = client.get(
            f"{API}/reports/{kind}?preset=all&format=csv", headers=shop.headers
        )
        assert csv.status_code == 200
        assert "text/csv" in csv.headers["content-type"]

        xlsx = client.get(
            f"{API}/reports/{kind}?preset=all&format=xlsx", headers=shop.headers
        )
        assert xlsx.status_code == 200

        pdf = client.get(
            f"{API}/reports/{kind}?preset=all&format=pdf", headers=shop.headers
        )
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF")

    standalone = client.get(f"{API}/reports/profit/pdf?preset=all", headers=shop.headers)
    assert standalone.status_code == 200


def test_cashier_cannot_pull_sales_reports(client: TestClient) -> None:
    shop = _trading_shop(client, email="rep2@test.com")
    cashier = factories.create_cashier(client, shop.headers, email="rep-c@test.com")
    assert client.get(f"{API}/reports/sales", headers=cashier).status_code == 403
