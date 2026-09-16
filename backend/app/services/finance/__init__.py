"""Finance service package — split from monolithic finance_service.py.

Modules:
    _utils      — date parsing, range resolution, memoization helpers
    _revenue    — revenue summary, sales-in-range, trend aggregation
    _expenses   — expense totals and breakdowns
    _analytics  — top products, customer stats, supplier stats
"""

from app.services.finance._analytics import customer_stats, supplier_stats, top_products
from app.services.finance._expenses import expense_breakdown, expense_summary
from app.services.finance._missing import (
    avg_costs,
    cogs_summary,
    expenses_total,
    inventory_value,
    profit_summary,
    sales_trend,
)
from app.services.finance._revenue import revenue_summary, revenue_trend, sales_in_range
from app.services.finance._utils import PRESETS, REVENUE_STATUSES, parse_dt, resolve_range

__all__ = [
    "PRESETS",
    "REVENUE_STATUSES",
    "avg_costs",
    "cogs_summary",
    "customer_stats",
    "expense_breakdown",
    "expense_summary",
    "expenses_total",
    "inventory_value",
    "parse_dt",
    "profit_summary",
    "resolve_range",
    "revenue_summary",
    "revenue_trend",
    "sales_in_range",
    "sales_trend",
    "supplier_stats",
    "top_products",
]
