"""AI endpoints (FR-30..FR-37) run offline: no Gemini key is required."""

from fastapi.testclient import TestClient

from tests import factories

API = "/api/v1"


def _shop_with_history(client: TestClient, email="ai@test.com"):
    shop = factories.seed_shop(client, email=email)
    factories.checkout(client, shop.headers, [{"product_id": shop.product_id, "quantity": 2}])
    return shop


def test_chat_answers_from_live_data_without_a_key(client: TestClient) -> None:
    shop = _shop_with_history(client)
    resp = client.post(
        f"{API}/ai/chat", json={"question": "What is our profit?"}, headers=shop.headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["answer"]
    assert "profit" in body["data"]
    assert body["recommendation_id"]  # save=True by default


def test_insights_forecast_reorder_and_anomalies_shape(
    client: TestClient,
) -> None:
    shop = _shop_with_history(client, email="ai2@test.com")
    insights = client.get(f"{API}/ai/insights", headers=shop.headers).json()
    assert "insights" in insights

    forecast = client.get(
        f"{API}/ai/forecast?product_id={shop.product_id}&days=30", headers=shop.headers
    ).json()
    assert "products" in forecast

    reorder = client.get(f"{API}/ai/reorder-recommendations?days=30", headers=shop.headers).json()
    assert "recommendations" in reorder

    anomalies = client.get(f"{API}/ai/anomalies", headers=shop.headers).json()
    assert "anomalies" in anomalies


def test_summarize_persists_a_recommendation(client: TestClient) -> None:
    shop = _shop_with_history(client, email="ai3@test.com")
    summary = client.post(
        f"{API}/ai/summarize",
        json={"kind": "profit", "preset": "all"},
        headers=shop.headers,
    )
    assert summary.status_code == 200, summary.text
    assert summary.json()["summary"]
    assert summary.json()["recommendation_id"]

    listing = client.get(f"{API}/ai/recommendations", headers=shop.headers).json()
    assert any(r["kind"] == "summary" for r in listing)


def test_recommendation_review_workflow(client: TestClient) -> None:
    shop = _shop_with_history(client, email="ai4@test.com")
    chat = client.post(
        f"{API}/ai/chat",
        json={"question": "Best seller?", "save": True},
        headers=shop.headers,
    )
    rid = chat.json()["recommendation_id"]

    updated = client.patch(
        f"{API}/ai/recommendations/{rid}",
        json={"reviewed": True, "acted_upon": True},
        headers=shop.headers,
    )
    assert updated.status_code == 200
    assert updated.json()["reviewed"] is True


def test_ai_endpoints_require_owner_or_manager(client: TestClient) -> None:
    shop = _shop_with_history(client, email="ai5@test.com")
    cashier = factories.create_cashier(client, shop.headers, email="ai-c@test.com")
    assert (
        client.post(f"{API}/ai/chat", json={"question": "hi"}, headers=cashier).status_code == 403
    )
    assert client.get(f"{API}/ai/insights", headers=cashier).status_code == 403
