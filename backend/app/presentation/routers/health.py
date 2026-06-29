"""Health check endpoints.

Used by Docker health checks, load balancers, and Kubernetes readiness probes.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, status
from sqlalchemy import text

from app.infrastructure.cache import check_redis_health
from app.infrastructure.database import engine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


async def check_db_health() -> bool:
    """Check database connectivity by executing a lightweight query."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("Database health check failed: %s", e)
        return False


@router.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict:
    """Basic liveness probe. Returns 200 if the process is running."""
    return {"status": "healthy", "service": "fraud-intelligence-api"}


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness() -> dict:
    """Readiness probe. Checks downstream dependencies."""
    checks: dict[str, bool] = {}

    # Redis health check
    checks["redis"] = await check_redis_health()

    # PostgreSQL health check
    checks["database"] = await check_db_health()

    # Determine overall status
    all_healthy = all(checks.values())

    return {
        "status": "ready" if all_healthy else "degraded",
        "checks": checks,
    }
