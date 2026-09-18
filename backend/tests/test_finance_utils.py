"""Tests for finance utility helpers: date parsing, range resolution, memoization."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from app.services.finance._utils import (
    MAX_SALE_IDS,
    MAX_TREND_BUCKETS,
    PRESETS,
    REVENUE_STATUSES,
    _memo_get,
    _memo_key,
    _memo_set,
    _sale_range_filters,
    parse_dt,
    resolve_range,
)


class TestParseDt:
    def test_none_returns_none(self) -> None:
        assert parse_dt(None) is None

    def test_datetime_passthrough(self) -> None:
        dt = datetime(2025, 1, 15, 10, 30)
        assert parse_dt(dt) is dt

    def test_valid_iso_string(self) -> None:
        assert parse_dt("2025-01-15T10:30:00") == datetime(2025, 1, 15, 10, 30, 0)

    def test_invalid_string_returns_none(self) -> None:
        assert parse_dt("not-a-date") is None


class TestResolveRange:
    def test_today(self) -> None:
        start, end = resolve_range("today")
        assert start is not None
        assert end is not None
        assert (end - start).total_seconds() < 86400

    def test_week(self) -> None:
        start, end = resolve_range("week")
        assert start is not None
        assert end is not None
        assert (end - start).days == 7

    def test_year(self) -> None:
        start, end = resolve_range("year")
        assert (end - start).days == 365

    def test_all_returns_none_bounds(self) -> None:
        start, end = resolve_range("all")
        assert start is None
        assert end is None

    def test_custom_with_dates(self) -> None:
        start, end = resolve_range("custom", date_from="2025-01-01", date_to="2025-01-31")
        assert start == datetime(2025, 1, 1)
        assert end == datetime(2025, 1, 31)

    def test_unknown_preset_defaults_to_month(self) -> None:
        start, end = resolve_range("nonsense")
        assert (end - start).days == 30

    def test_default_preset_is_month(self) -> None:
        start, end = resolve_range()
        assert (end - start).days == 30


class TestMemo:
    def test_memo_key_is_deterministic(self) -> None:
        key = _memo_key(1, "2025-01-01", "2025-01-31")
        assert key == (1, "2025-01-01", "2025-01-31")

    def test_memo_get_miss_returns_none(self) -> None:
        db = MagicMock()
        assert _memo_get(db, "fn", 1, "a", "b") is None

    def test_memo_get_hit_returns_copy(self) -> None:
        db = MagicMock()
        cache = {("fn", (1, "a", "b")): {"result": 1}}
        db._fin_cache = cache  # type: ignore[attr-defined]
        result = _memo_get(db, "fn", 1, "a", "b")
        assert result == {"result": 1}

    def test_memo_set_stores_and_returns(self) -> None:
        db = MagicMock()
        db._fin_cache = None  # type: ignore[attr-defined]
        result = _memo_set(db, "fn", 1, "a", "b", {"result": 42})
        assert result == {"result": 42}
        cache = db._fin_cache
        assert cache[("fn", (1, "a", "b"))] == {"result": 42}


class TestConstants:
    def test_constants_are_int(self) -> None:
        assert isinstance(MAX_SALE_IDS, int)
        assert isinstance(MAX_TREND_BUCKETS, int)

    def test_preset_and_status_constants(self) -> None:
        assert "month" in PRESETS
        assert "completed" in REVENUE_STATUSES


class TestSaleRangeFilters:
    def test_filters_without_dates(self) -> None:
        flt = _sale_range_filters(1, None, None)
        assert len(flt) == 2  # business_id + status filter

    def test_filters_with_dates(self) -> None:
        flt = _sale_range_filters(1, "2025-01-01", "2025-01-31")
        assert len(flt) == 4  # business_id + status + start + end
