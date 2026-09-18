"""Revenue-related finance queries: summaries, trends, sales-in-range."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.finance import Expense
from app.models.sales import Sale
from app.services.finance._utils import (
    MAX_SALE_IDS,
    MAX_TREND_BUCKETS,
    _memo_get,
    _memo_set,
    _sale_range_filters,
)


def sales_in_range(db: Session, business_id: int, start, end):
    """Fetch sales rows for a period. Bounded + newest-first to prevent OOM."""
    q = db.query(Sale).filter(*_sale_range_filters(business_id, start, end))
    return q.order_by(Sale.id.desc()).limit(MAX_SALE_IDS).all()


def revenue_summary(db: Session, business_id: int, start: object, end: object) -> dict:
    """FR-16: gross/net revenue + order count for a period (single SQL query)."""
    hit = _memo_get(db, "revenue_summary", business_id, start, end)
    if isinstance(hit, dict):
        return hit
    row = (
        db.query(
            func.count(Sale.id),
            func.coalesce(func.sum(Sale.total_amount), 0),
            func.coalesce(func.sum(Sale.paid_amount), 0),
        )
        .filter(*_sale_range_filters(business_id, start, end))
        .first()
    )
    expense = (
        db.query(func.coalesce(func.sum(Expense.amount), 0))
        .filter(
            Expense.business_id == business_id,
            *([Expense.expense_date >= start] if start is not None else []),
            *([Expense.expense_date <= end] if end is not None else []),
        )
        .scalar()
    )
    gross = round(float(row[1] or 0) if row is not None else 0.0, 2)
    collected = round(float(row[2] or 0) if row is not None else 0.0, 2)
    exp_total = round(float(expense or 0), 2)
    orders = int(row[0] or 0) if row is not None else 0
    result = {
        "orders": orders,
        "revenue": gross,
        "collected": collected,
        "expenses": exp_total,
        "net_profit": round(gross - exp_total, 2),
        "gross_revenue": gross,
        "net_revenue": gross,
        "total_expenses": exp_total,
        "refunded": 0.0,
        "total_amount": gross,
    }
    return _memo_set(db, "revenue_summary", business_id, start, end, result)


def _bucket_key(dt, bucket: str) -> str:
    """Portable period key: identical output on SQLite and Postgres."""
    if bucket == "month":
        return dt.strftime("%Y-%m")
    if bucket == "week":
        iso = dt.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    return dt.strftime("%Y-%m-%d")


def revenue_trend(db: Session, business_id: int, start, end, bucket: str = "day") -> list[dict]:
    """FR-18: revenue trend grouped by day/week/month (dialect-portable).

    Grouped in Python over ``(created_at, total_amount)`` pairs so the suite
    passes on SQLite while production Postgres returns identical buckets.
    """
    pairs = (
        db.query(Sale.created_at, Sale.total_amount)
        .filter(*_sale_range_filters(business_id, start, end))
        .order_by(Sale.created_at.asc())
        .limit(MAX_SALE_IDS)
        .all()
    )
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    for created_at, total in pairs:
        key = _bucket_key(created_at, bucket)
        totals[key] = totals.get(key, 0.0) + float(total or 0)
        counts[key] = counts.get(key, 0) + 1
    return [
        {"period": key, "orders": counts[key], "revenue": round(totals[key], 2)}
        for key in sorted(totals)
    ][:MAX_TREND_BUCKETS]
