"""Tests for deterministic AI answer-building (ai_service._rule_answer, _business_snapshot)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services import ai_service


class TestBusinessSnapshot:
    @patch.object(ai_service.f, "resolve_range")
    @patch.object(ai_service.f, "profit_summary")
    @patch.object(ai_service.f, "sales_trend")
    @patch.object(ai_service.f, "top_products")
    @patch.object(ai_service.f, "customer_stats")
    @patch.object(ai_service.f, "supplier_stats")
    @patch.object(ai_service.f, "inventory_value")
    def test_snapshot_assembles_all_sections(
        self, mock_inv, mock_supp, mock_cust, mock_top, mock_trend, mock_profit, mock_range
    ) -> None:
        mock_range.return_value = ("s", "e")
        mock_profit.return_value = {"gross_profit": 100, "net_profit": 50}
        mock_trend.return_value = [{"period": "d1", "revenue": 10}]
        mock_top.return_value = [{"product_name": "Widget", "quantity": 5}]
        mock_cust.return_value = [{"customer_name": "A", "spent": 10}]
        mock_supp.return_value = [{"supplier_name": "S", "purchased": 20}]
        mock_inv.return_value = {"units": 100, "skus": 5, "cost_value": 50, "retail_value": 100}

        snap = ai_service._business_snapshot(MagicMock(), 1, preset="week")

        assert snap["preset"] == "week"
        assert snap["profit"]["gross_profit"] == 100
        assert snap["trend"][0]["period"] == "d1"
        assert snap["top_products"][0]["product_name"] == "Widget"
        assert snap["customers"][0]["customer_name"] == "A"
        assert snap["suppliers"][0]["supplier_name"] == "S"
        assert snap["inventory"]["units"] == 100

    @patch.object(ai_service.f, "resolve_range")
    def test_snapshot_unknown_preset_defaults_to_month(self, mock_range) -> None:
        mock_range.return_value = ("s", "e")
        with (
            patch.object(ai_service.f, "profit_summary", return_value={}),
            patch.object(ai_service.f, "sales_trend", return_value=[]),
            patch.object(ai_service.f, "top_products", return_value=[]),
            patch.object(ai_service.f, "customer_stats", return_value=[]),
            patch.object(ai_service.f, "supplier_stats", return_value=[]),
            patch.object(ai_service.f, "inventory_value", return_value={}),
        ):
            snap = ai_service._business_snapshot(MagicMock(), 1, preset="bogus")
            mock_range.assert_called_with("month")
            assert snap["preset"] == "bogus"
