"""Tests for the datetime bucketing helper and revenue service functions."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from app.services.finance._revenue import (
    _bucket_key,
    revenue_summary,
    revenue_trend,
    sales_in_range,
)


class TestBucketKey:
    def test_month_bucket(self) -> None:
        dt = datetime(2025, 1, 15, 10, 30)
        assert _bucket_key(dt, "month") == "2025-01"

    def test_week_bucket(self) -> None:
        dt = datetime(2025, 1, 15)  # Wednesday of week 3
        result = _bucket_key(dt, "week")
        assert result.startswith("2025-W")

    def test_day_bucket(self) -> None:
        dt = datetime(2025, 1, 15, 10, 30)
        assert _bucket_key(dt, "day") == "2025-01-15"


def _chain(db: MagicMock) -> MagicMock:
    """Helper: return the terminal .all() mock for a query chain."""
    return db.query.return_value.filter.return_value.order_by.return_value.limit.return_value


class TestSalesInRange:
    def test_sales_in_range_returns_list(self) -> None:
        db = MagicMock()
        _chain(db).all.return_value = [MagicMock(id=1), MagicMock(id=2)]
        result = sales_in_range(db, business_id=1, start=None, end=None)
        assert len(result) == 2

    def test_sales_in_range_empty(self) -> None:
        db = MagicMock()
        _chain(db).all.return_value = []
        result = sales_in_range(db, business_id=1, start=None, end=None)
        assert result == []


class TestRevenueSummary:
    def test_revenue_summary_no_memo_hit(self) -> None:
        db = MagicMock()
        # No cache -> _memo_get returns None -> computes fresh
        db._fin_cache = None  # type: ignore[attr-defined]
        db.query.return_value.filter.return_value.first.return_value = (10, 5000.0, 4500.0)
        db.query.return_value.filter.return_value.scalar.return_value = 500.0

        result = revenue_summary(db, business_id=1, start=None, end=None)

        assert result["orders"] == 10
        assert result["revenue"] == 5000.0
        assert result["collected"] == 4500.0
        assert result["expenses"] == 500.0
        assert result["net_profit"] == 4500.0

    def test_revenue_summary_memo_hit(self) -> None:
        cached = {"orders": 5, "revenue": 1000.0}
        db = MagicMock()
        db._fin_cache = {("revenue_summary", (1, str(None), str(None))): cached}  # type: ignore

        result = revenue_summary(db, business_id=1, start=None, end=None)

        assert result == cached
        db.query.assert_not_called()


class TestRevenueTrend:
    def test_revenue_trend_empty(self) -> None:
        db = MagicMock()
        _chain(db).all.return_value = []
        result = revenue_trend(db, business_id=1, start=None, end="2025-01-31")
        assert result == []
