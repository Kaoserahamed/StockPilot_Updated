import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models as _models  # noqa: F401  (importing registers every SQLAlchemy mapper)
from app.api import health as health_api
from app.api.v1 import ai as ai_api
from app.api.v1 import (
    analytics,
    audit,
    auth,
    businesses,
    categories,
    employees,
    expenses,
    finance,
    inventory,
    invoices,
    parties,
    products,
    purchases,
    reports,
    returns,
    sales,
)
from app.api.v1 import settings as settings_api
from app.api.v1 import subscription as subscription_api
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import setup_logging
from app.core.middleware import register_middleware
from app.core.timeouts import setup_timeouts
from app.db.base import Base
from app.db.session import engine, ensure_indexes

# Setup structured logging
setup_logging(level=settings.log_level, json_format=settings.json_logs)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager."""
    # Startup
    logger.info("Starting %s (env=%s)", settings.app_name, settings.environment)
    # Phase-1 convenience; Alembic migrations take over in production.
    Base.metadata.create_all(bind=engine)
    ensure_indexes()
    logger.info("Database initialized and indexes ensured")

    yield

    # Shutdown
    logger.info("Shutting down %s", settings.app_name)
    engine.dispose()
    logger.info("Database connections closed")


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    description="""
## StockPilot API - Inventory & POS SaaS

Multi-tenant inventory management, point-of-sale, finance tracking, and AI insights
for small businesses.

### Authentication
All API endpoints require a Bearer token in the Authorization header:
`Authorization: Bearer <access_token>`

Include the business ID in the X-Business-Id header:
`X-Business-Id: <business_id>`

### Rate Limiting
- Default: 100 requests per minute per user
- Auth endpoints: 5 requests per minute per IP

### Support
For issues and feature requests, contact support.
""",
    version="1.0.0",
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url="/redoc" if settings.environment != "production" else None,
)

# --- Custom middleware (security headers, request context) ---
register_middleware(app)

# --- Request timeouts ---
setup_timeouts(app)

# --- CORS (registered LAST so it is outermost and wraps every response,
# --- including timeout 504s, with Access-Control headers) ---
# A wildcard origin can never be combined with credentials: browsers reject
# `Access-Control-Allow-Origin: *` + `Allow-Credentials: true`, and it hides
# origin-allowlist bugs. Wildcard => no credentials; explicit origins => yes.
if settings.cors_origins.strip() == "*":
    allowed_origins = ["*"]
    allow_credentials = False
else:
    allowed_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Exception handlers ---
register_exception_handlers(app)

# --- Health check endpoints ---
app.include_router(health_api.router)


@app.get("/", include_in_schema=False)
def root():
    """Root endpoint — returns basic API info."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1",
    }


# --- Audit trail (FR-27) ---
app.include_router(audit.router, prefix="/api/v1")


# --- API v1 routers ---
app.include_router(auth.router, prefix="/api/v1")
app.include_router(businesses.router, prefix="/api/v1")
app.include_router(employees.router, prefix="/api/v1")
app.include_router(categories.router, prefix="/api/v1")
app.include_router(products.router, prefix="/api/v1")
app.include_router(parties.router, prefix="/api/v1")
app.include_router(inventory.router, prefix="/api/v1")
app.include_router(purchases.router, prefix="/api/v1")
app.include_router(sales.router, prefix="/api/v1")
app.include_router(invoices.router, prefix="/api/v1")
app.include_router(returns.router, prefix="/api/v1")
app.include_router(expenses.router, prefix="/api/v1")
app.include_router(finance.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(settings_api.router, prefix="/api/v1")
app.include_router(subscription_api.router, prefix="/api/v1")
app.include_router(ai_api.router, prefix="/api/v1")
