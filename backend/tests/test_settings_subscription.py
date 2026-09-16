"""Settings and subscriptions (FR-28, FR-29)."""

from fastapi.testclient import TestClient

from tests import factories

API = "/api/v1"


def test_settings_read_update_round_trip(client: TestClient) -> None:
    headers = factories.register_owner(client, email="set@test.com")
    before = client.get(f"{API}/settings", headers=headers).json()
    assert before["currency"] == "BDT"

    updated = client.patch(
        f"{API}/settings",
        json={"currency": "USD", "tax_rate": 7.5, "min_stock_default": 3},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["currency"] == "USD"
    assert body["tax_rate"] == 7.5
    assert body["min_stock_default"] == 3


def test_only_owners_change_settings_and_plans(client: TestClient) -> None:
    headers = factories.register_owner(client, email="set2@test.com")
    manager = factories.create_employee(
        client, headers, name="M", email="m-set2@test.com", role="Manager"
    )
    manager_headers = factories.login(client, manager["user"]["email"])

    assert (
        client.patch(
            f"{API}/settings", json={"currency": "USD"}, headers=manager_headers
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"{API}/subscription", json={"plan": "pro"}, headers=manager_headers
        ).status_code
        == 403
    )


def test_subscription_reports_usage_and_plan_changes(client: TestClient) -> None:
    shop = factories.seed_shop(client, email="sub@test.com")
    status = client.get(f"{API}/subscription", headers=shop.headers).json()
    assert status["plan"] == "free"
    assert status["product_count"] >= 1
    assert status["employee_count"] >= 1

    upgraded = client.patch(f"{API}/subscription", json={"plan": "pro"}, headers=shop.headers)
    assert upgraded.status_code == 200, upgraded.text
    assert upgraded.json()["plan"] == "pro"

    invalid = client.post(f"{API}/subscription", json={"plan": "enterprise"}, headers=shop.headers)
    assert invalid.status_code in (404, 405, 422)

    bad = client.patch(f"{API}/subscription", json={"plan": "enterprise"}, headers=shop.headers)
    assert bad.status_code == 422
