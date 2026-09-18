"""Tests for the pagination helper."""

from unittest.mock import MagicMock

from app.core.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, paginated_response


def _make_query(items: list, total: int) -> MagicMock:
    query = MagicMock()
    query.count.return_value = total
    query.offset.return_value.limit.return_value.all.return_value = items
    return query


def test_paginated_response_with_items_and_more() -> None:
    items = [{"id": 1}, {"id": 2}]
    query = _make_query(items, total=100)

    result = paginated_response(query, limit=2, offset=0)

    assert result["items"] == items
    assert result["pagination"]["total"] == 100
    assert result["pagination"]["limit"] == 2
    assert result["pagination"]["offset"] == 0
    assert result["pagination"]["has_more"] is True
    assert result["pagination"]["next_offset"] == 2


def test_paginated_response_last_page_has_no_next_offset() -> None:
    query = _make_query([], total=10)

    result = paginated_response(query, limit=5, offset=5)

    assert result["pagination"]["has_more"] is False
    assert result["pagination"]["next_offset"] is None
    assert result["pagination"]["total"] == 10


def test_paginated_response_empty_result() -> None:
    query = _make_query([], total=0)

    result = paginated_response(query, limit=DEFAULT_PAGE_SIZE, offset=0)

    assert result["items"] == []
    assert result["pagination"]["total"] == 0
    assert result["pagination"]["has_more"] is False
    assert result["pagination"]["next_offset"] is None


def test_paginated_response_respects_max_page_size_constant() -> None:
    assert MAX_PAGE_SIZE == 200
    assert DEFAULT_PAGE_SIZE == 50
