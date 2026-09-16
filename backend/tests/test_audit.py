"""Audit trail (FR-27): who changed what, tenant-scoped and role-gated."""

from fastapi.testclient import TestClient

from tests import factories

API = "/api/v1"


def test_audit_trail_records_catalogue_and_stock_changes(client: TestClient, shop) -> None:
    factories.adjust_stock(client, shop.headers, shop.product_id, 3, reason="recount")

    logs = client.get(f"{API}/audit-logs", headers=shop.headers).json()
    assert logs, "expected at least one audit entry"
    actions = [row["action"] for row in logs]
    assert "inventory.adjust" in actions

    entry = logs[0]
    assert entry["resource"]
    assert entry["created_at"]


def test_audit_trail_filters_by_action_and_resource(client: TestClient, shop) -> None:
    factories.adjust_stock(client, shop.headers, shop.product_id, 1, reason="count")

    by_action = client.get(f"{API}/audit-logs?action=inventory.adjust", headers=shop.headers).json()
    assert by_action and all(row["action"] == "inventory.adjust" for row in by_action)

    by_resource = client.get(f"{API}/audit-logs?resource=product", headers=shop.headers).json()
    assert all(row["resource"] == "product" for row in by_resource)


def test_audit_trail_respects_the_limit_parameter(client: TestClient, shop) -> None:
    for _ in range(5):
        factories.adjust_stock(client, shop.headers, shop.product_id, 1, reason="tick")
    limited = client.get(f"{API}/audit-logs?limit=2", headers=shop.headers).json()
    assert len(limited) == 2


def test_audit_trail_is_tenant_scoped(client: TestClient) -> None:
    first = factories.seed_shop(client, email="audit-a@test.com")
    second = factories.seed_shop(client, email="audit-b@test.com")
    factories.adjust_stock(client, first.headers, first.product_id, 4, reason="mine")

    other_ids = {
        row["id"] for row in client.get(f"{API}/audit-logs", headers=second.headers).json()
    }
    mine_ids = {row["id"] for row in client.get(f"{API}/audit-logs", headers=first.headers).json()}
    assert mine_ids.isdisjoint(other_ids)
    assert mine_ids


def test_cashier_cannot_read_the_audit_trail(client: TestClient, shop) -> None:
    cashier = factories.create_cashier(client, shop.headers, email="audit-c@test.com")
    assert client.get(f"{API}/audit-logs", headers=cashier).status_code == 403
    assert client.get(f"{API}/audit-logs").status_code == 401
