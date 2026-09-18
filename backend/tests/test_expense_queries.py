"""Tests for the expense finance service functions."""

from unittest.mock import MagicMock

from app.services.finance._expenses import expense_breakdown, expense_summary


def _make_row(count: int, total: float) -> MagicMock:
    row = MagicMock()
    row.__getitem__ = MagicMock(side_effect=lambda i: [count, total][i])
    return row


def test_expense_summary_with_results() -> None:
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = _make_row(5, 1500.0)

    result = expense_summary(db, business_id=1, start=None, end=None)

    assert result == {"count": 5, "total": 1500.0}


def test_expense_summary_no_rows() -> None:
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    result = expense_summary(db, business_id=1, start=None, end=None)

    assert result == {"count": 0, "total": 0.0}


def test_expense_summary_with_date_filter() -> None:
    db = MagicMock()
    filtered = MagicMock()
    db.query.return_value.filter.return_value = filtered
    filtered.first.return_value = _make_row(3, 750.0)

    result = expense_summary(db, business_id=1, start="2025-01-01", end="2025-01-31")

    assert result == {"count": 3, "total": 750.0}


def test_expense_breakdown() -> None:
    db = MagicMock()
    rows = [
        ("Supplies", 2, 300.0),
        ("Shipping", 1, 500.0),
    ]
    db.query.return_value.filter.return_value.group_by.return_value.all.return_value = rows

    result = expense_breakdown(db, business_id=1, start=None, end=None)

    assert result == [
        {"category": "Supplies", "count": 2, "total": 300.0},
        {"category": "Shipping", "count": 1, "total": 500.0},
    ]


def test_expense_breakdown_empty() -> None:
    db = MagicMock()
    db.query.return_value.filter.return_value.group_by.return_value.all.return_value = []

    result = expense_breakdown(db, business_id=1, start=None, end=None)

    assert result == []
