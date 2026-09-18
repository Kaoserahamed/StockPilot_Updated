"""Tests for the ai3_service: reorder recommendations and anomaly detection."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from app.services.ai3_service import (
    detect_anomalies,
    reorder_recommendations,
    summarize_report,
)


class TestReorderRecommendations:
    @patch("app.services.ai2_service.forecast_demand")
    def test_reorder_with_need(self, mock_fc) -> None:
        mock_fc.return_value = {
            "forecast_days": 30,
            "products": [
                {"product_id": 1, "product_name": "A", "predicted_demand": 10},
                {"product_id": 2, "product_name": "B", "predicted_demand": 0},
            ],
        }
        db = MagicMock()
        p1 = MagicMock(id=1, min_stock=5, quantity_on_hand=3)
        p2 = MagicMock(id=2, min_stock=2, quantity_on_hand=10)
        db.query.return_value.filter.return_value.all.return_value = [p1, p2]

        result = reorder_recommendations(db, business_id=1)

        assert result["forecast_days"] == 30
        assert len(result["needs_reorder"]) == 1
        assert result["needs_reorder"][0]["product_id"] == 1

    @patch("app.services.ai2_service.forecast_demand")
    def test_reorder_no_products(self, mock_fc) -> None:
        mock_fc.return_value = {"forecast_days": 30, "products": []}
        db = MagicMock()
        db.query.return_value.filter.return_value.all.return_value = []

        result = reorder_recommendations(db, business_id=1)

        assert result["recommendations"] == []
        assert result["needs_reorder"] == []


class TestDetectAnomalies:
    @patch("app.services.finance_service._sale_range_filters")
    @patch("app.services.finance_service.MAX_SALE_IDS", 20000)
    @patch("app.models.sales.Sale")
    def test_no_data_returns_empty(self, mock_sale, mock_filters) -> None:
        mock_filters.return_value = []
        db = MagicMock()
        chain = db.query.return_value.filter.return_value.order_by.return_value.limit.return_value
        chain.all.return_value = []

        result = detect_anomalies(db, business_id=1)
        assert result == {"anomalies": [], "count": 0}

    @patch("app.services.finance_service._sale_range_filters")
    @patch("app.services.finance_service.MAX_SALE_IDS", 20000)
    @patch("app.models.sales.Sale")
    def test_revenue_outlier_detected(self, mock_sale, mock_filters) -> None:
        mock_filters.return_value = []
        db = MagicMock()
        date_rows = [
            (datetime(2025, 1, 1), 100.0),
            (datetime(2025, 1, 2), 100.0),
            (datetime(2025, 1, 3), 100.0),
            (datetime(2025, 1, 4), 100.0),
            (datetime(2025, 1, 5), 1000.0),
        ]
        sale_rows = [(1, "INV-001", 100.0), (2, "INV-002", 1000.0)]
        chain = db.query.return_value.filter.return_value.order_by.return_value.limit.return_value
        chain.all.side_effect = [date_rows, sale_rows]

        result = detect_anomalies(db, business_id=1)
        assert result["count"] >= 1
        assert any(a["type"] == "daily_revenue_outlier" for a in result["anomalies"])


class TestSummarizeReport:
    def test_profit_summary(self) -> None:
        result = summarize_report(
            "profit",
            {
                "net_revenue": 100,
                "orders": 5,
                "cogs": 20,
                "total_expenses": 30,
                "gross_profit": 50,
                "net_profit": 50,
            },
        )
        assert "Insight" in result
        assert "100" in result

    def test_sales_summary(self) -> None:
        result = summarize_report(
            "sales",
            {"orders": 5, "gross_revenue": 500, "refunded": 0, "net_revenue": 500},
        )
        assert "Sales" in result

    def test_expenses_summary(self) -> None:
        result = summarize_report(
            "expenses",
            {"summary": {"total_expenses": 100}, "rows": [{"a": 1}, {"b": 2}]},
        )
        assert "Expenses" in result

    def test_inventory_summary(self) -> None:
        result = summarize_report(
            "inventory",
            {"summary": {"units": 50, "skus": 5, "cost_value": 100, "retail_value": 200}},
        )
        assert "Inventory" in result

    def test_unknown_kind(self) -> None:
        result = summarize_report("unknown", {})
        assert "Summary" in result
