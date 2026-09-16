"""Finance service - backward-compatible re-export from finance subpackage.

This module now delegates to smaller, focused modules under app/services/finance/.
New code should import directly from app.services.finance.
Existing imports from app.services.finance_service continue to work.
"""

# Re-export everything from the new subpackage
from app.services.finance import (
    PRESETS,
    REVENUE_STATUSES,
    customer_stats,
    expense_breakdown,
    expense_summary,
    parse_dt,
    resolve_range,
    revenue_summary,
    revenue_trend,
    sales_in_range,
    supplier_stats,
    top_products,
)
from app.services.finance._missing import (
    avg_costs,
    cogs_summary,
    expenses_total,
    inventory_value,
    profit_summary,
    sales_trend,
)
from app.services.finance._utils import (
    MAX_SALE_IDS,
    MAX_TREND_BUCKETS,
    _sale_range_filters,
)

__all__ = [
    "MAX_SALE_IDS",
    "MAX_TREND_BUCKETS",
    "PRESETS",
    "REVENUE_STATUSES",
    "_sale_range_filters",
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
