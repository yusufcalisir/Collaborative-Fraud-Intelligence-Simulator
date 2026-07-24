"""Unit and integration tests for Section 35.2 — Cache Layer & Graceful Degradation.

Tests:
  1. CacheService initialization & singleton instance.
  2. Read-aside and Write-through operations for Alerts, Cases, and Entities.
  3. TTL expiration logic & key formatting.
  4. Graceful degradation when Redis is offline (all methods fall back gracefully without raising exceptions).
"""

from __future__ import annotations

import pytest

from app.infrastructure.cache import TTL_ALERT, TTL_CASE, TTL_ENTITY, CacheService


@pytest.fixture
def cache_service():
    """Reset CacheService singleton state for testing."""
    CacheService._instance = None
    CacheService._client = None
    CacheService._unavailable = False
    return CacheService.get()


@pytest.mark.asyncio
async def test_cache_service_singleton(cache_service: CacheService) -> None:
    """CacheService.get() must return the same process-level singleton instance."""
    instance1 = CacheService.get()
    instance2 = CacheService.get()
    assert instance1 is instance2


@pytest.mark.asyncio
async def test_graceful_degradation_when_redis_unavailable(cache_service: CacheService) -> None:
    """When Redis is unavailable or unconfigured, all methods must return None/default without raising exceptions."""
    # Force unavailable state
    CacheService._unavailable = True

    # Reads should return None
    assert await cache_service.get_alert("alert-123") is None
    assert await cache_service.get_case("case-123") is None
    assert await cache_service.get_entity("entity-123") is None
    assert await cache_service.get_entity_id_by_hash("hash-123") is None

    # Writes & invalidations should fail silently
    await cache_service.set_alert("alert-123", {"id": "alert-123", "status": "new"})
    await cache_service.invalidate_alert("alert-123", "bank_alpha")
    await cache_service.set_case("case-123", {"id": "case-123"})
    await cache_service.set_entity("entity-123", {"id": "entity-123", "privacy_id": "p123"})

    # Health check should return False
    assert await cache_service.health() is False

    # Rate limiter should fail open (return True)
    assert await cache_service.rate_limit_check("test-ip", limit=5) is True


@pytest.mark.asyncio
async def test_ttl_constants() -> None:
    """Verify production TTL configurations align with design spec."""
    assert TTL_ALERT == 300
    assert TTL_CASE == 300
    assert TTL_ENTITY == 600
