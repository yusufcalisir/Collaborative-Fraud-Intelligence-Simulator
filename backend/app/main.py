"""FastAPI application entry point.

Wires together all routers, middleware, and lifecycle hooks.
"""
# ruff: noqa: E402

from __future__ import annotations

import logging
import os
import sys

# Set threads to 1 during test suite run to prevent C++ teardown aborts under pytest-cov,
# but keep it at 2 in production/dev for max performance.
is_testing = (
    "pytest" in sys.modules
    or any("pytest" in arg for arg in sys.argv)
    or "PYTEST_CURRENT_TEST" in os.environ
    or os.environ.get("GITHUB_ACTIONS") == "true"
)
num_threads_str = "1" if is_testing else "2"

os.environ["OMP_NUM_THREADS"] = num_threads_str
os.environ["MKL_NUM_THREADS"] = num_threads_str
os.environ["OPENBLAS_NUM_THREADS"] = num_threads_str
os.environ["VECLIB_MAXIMUM_THREADS"] = num_threads_str
os.environ["NUMEXPR_NUM_THREADS"] = num_threads_str

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.presentation.routers import (
    alerts,
    banks,
    cases,
    dashboard,
    entities,
    graph,
    health,
    scenarios,
    simulation,
    training,
)
from app.presentation.websockets import streaming_ws, training_ws

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# ── Logging ───────────────────────────────────
settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.app_log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifecycle ─────────────────────────────────
# ── Lifecycle ─────────────────────────────────
def seed_mock_data() -> None:
    """Seed initial mock data for Phase 2 AML platform."""
    from app.domain.entities_phase2 import Alert, SharedIntelligence
    from app.domain.enums import (
        AlertSeverity,
        AlertStatus,
        CasePriority,
        CaseStatus,
        EntityType,
        IntelligenceType,
        RelationshipType,
        RiskLevel,
    )
    from app.presentation.routers.alerts import get_alert_service
    from app.presentation.routers.cases import get_case_service
    from app.presentation.routers.entities import get_entity_service
    from app.presentation.routers.graph import get_graph_engine

    alert_svc = get_alert_service()
    case_svc = get_case_service()
    entity_svc = get_entity_service()
    graph_engine = get_graph_engine()

    # Clear existing to be idempotent
    alert_svc._alert_store.clear()
    alert_svc._intelligence_store.clear()
    case_svc._cases.clear()
    entity_svc._entities.clear()
    entity_svc._relationships.clear()
    entity_svc._hash_index.clear()
    graph_engine._entities.clear()
    graph_engine._relationships.clear()
    graph_engine._adjacency.clear()

    # 1. Create seed entities
    c1 = entity_svc.create_entity(
        EntityType.CUSTOMER,
        "user_john_doe",
        "bank_a",
        {"risk_score": 0.12, "bank_name": "Meridian National"},
    )
    c2 = entity_svc.create_entity(
        EntityType.CUSTOMER,
        "user_jane_smith",
        "bank_b",
        {"risk_score": 0.85, "bank_name": "Nexus Digital"},
    )
    c3 = entity_svc.create_entity(
        EntityType.CUSTOMER,
        "user_bob_jones",
        "bank_c",
        {"risk_score": 0.45, "bank_name": "Heritage Regional"},
    )

    dev1 = entity_svc.create_entity(
        EntityType.DEVICE, "device_secure_token_99", "bank_a", {"device_type": "mobile_app"}
    )
    dev2 = entity_svc.create_entity(
        EntityType.DEVICE, "device_secure_token_99", "bank_b", {"device_type": "mobile_app"}
    )

    m1 = entity_svc.create_entity(
        EntityType.MERCHANT, "merchant_crypto_exchange", "bank_b", {"category": "crypto"}
    )
    m2 = entity_svc.create_entity(
        EntityType.MERCHANT, "merchant_luxury_store", "bank_c", {"category": "luxury"}
    )

    for e in [c1, c2, c3, dev1, dev2, m1, m2]:
        graph_engine.register_entity(e)

    # 2. Create relationships
    r1 = entity_svc.add_relationship(c1.id, dev1.id, RelationshipType.USES, confidence=1.0)
    r2 = entity_svc.add_relationship(c2.id, dev2.id, RelationshipType.USES, confidence=1.0)
    r3 = entity_svc.add_relationship(c2.id, m1.id, RelationshipType.TRANSACTS_WITH, confidence=0.95)
    r4 = entity_svc.add_relationship(c3.id, m2.id, RelationshipType.TRANSACTS_WITH, confidence=0.80)
    r5 = entity_svc.add_relationship(
        dev1.id, dev2.id, RelationshipType.SHARES_DEVICE, confidence=1.0
    )

    for r in [r1, r2, r3, r4, r5]:
        graph_engine.add_relationship(r)

    # 3. Create mock alerts
    a1 = Alert(
        bank_id="bank_b",
        transaction_id="tx_98234",
        risk_score=850.0,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.NEW,
        reason_codes=["VEL-001", "DEV-ANOM"],
        confidence=0.85,
        involved_entity_ids=[c2.id],
        model_confidence=0.85,
        top_features=[
            {"feature": "velocity", "value": 0.92},
            {"feature": "new_device", "value": 1.0},
        ],
        risk_factors=[
            "Rapid transfer immediately after device change",
            "Unusual high-risk merchant destination",
        ],
    )
    alert_svc._alert_store[a1.id] = a1
    entity_svc.increment_alert_count(c2.id)
    entity_svc.update_risk_level(c2.id, RiskLevel.HIGH)

    a2 = Alert(
        bank_id="bank_c",
        transaction_id="tx_12049",
        risk_score=450.0,
        severity=AlertSeverity.MEDIUM,
        status=AlertStatus.NEW,
        reason_codes=["AMT-ANOM"],
        confidence=0.45,
        involved_entity_ids=[c3.id],
        model_confidence=0.45,
        top_features=[{"feature": "amount", "value": 0.78}],
        risk_factors=["Transaction amount significantly exceeds customer historical average"],
    )
    alert_svc._alert_store[a2.id] = a2
    entity_svc.increment_alert_count(c3.id)
    entity_svc.update_risk_level(c3.id, RiskLevel.MEDIUM)

    # 4. Create mock case
    case = case_svc.create_case(
        title="High-Risk Activity: Device Sharing & Crypto Outflow",
        priority=CasePriority.P2_HIGH,
        alert_ids=[a1.id],
    )
    case.assigned_to = "senior_analyst_1"
    case.status = CaseStatus.INVESTIGATING

    # 5. Create shared intelligence
    intel = SharedIntelligence(
        source_bank_id="bank_b",
        intelligence_type=IntelligenceType.FRAUD_ALERT,
        privacy_hash=dev1.privacy_id,
        risk_indicator=0.85,
        description="High-risk device hash associated with rapid account takeovers",
        entity_type=EntityType.DEVICE,
        related_alert_count=1,
    )
    alert_svc._intelligence_store.append(intel)
    logger.info("Successfully seeded mock data for Phase 2")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown hooks."""
    logger.info("Starting Collaborative Fraud Intelligence Simulator")
    logger.info("Environment: %s", settings.app_env)

    # Ensure PyTorch threading limits are applied at runtime
    import torch

    is_testing_run = (
        "pytest" in sys.modules
        or any("pytest" in arg for arg in sys.argv)
        or "PYTEST_CURRENT_TEST" in os.environ
        or os.environ.get("GITHUB_ACTIONS") == "true"
    )
    num_threads = 1 if is_testing_run else 2

    try:
        torch.set_num_threads(num_threads)
        torch.set_num_interop_threads(num_threads)
    except RuntimeError as e:
        logger.warning("Could not set PyTorch threading limits: %s", e)

    # Seed mock data
    try:
        seed_mock_data()
    except Exception as exc:
        logger.error("Failed to seed mock data: %s", exc, exc_info=True)

    yield
    logger.info("Shutting down")


# ── Application ───────────────────────────────
app = FastAPI(
    title="Collaborative Fraud Intelligence Simulator",
    description=(
        "Privacy-preserving cross-institution fraud detection using Federated Learning. "
        "Simulates collaborative model training between three independent banks without "
        "sharing raw transaction data. Phase 2 adds collaborative alert intelligence, "
        "risk scoring, case management, entity resolution, and relationship graphs."
    ),
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────
# Allow all origins and disable credentials to avoid any CORS issues on Vercel preview/production links.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ───────────────────────────────────
# Phase 1: Federated Learning
app.include_router(health.router)
app.include_router(simulation.router)
app.include_router(banks.router)
app.include_router(training.router)
app.include_router(training_ws.router)

# Phase 2: AML Intelligence Platform
app.include_router(alerts.router)
app.include_router(cases.router)
app.include_router(entities.router)
app.include_router(graph.router)
app.include_router(scenarios.router)
app.include_router(dashboard.router)
app.include_router(streaming_ws.router)


@app.get("/", tags=["root"])
async def root() -> dict:
    """API root — returns basic service info."""
    return {
        "service": "Collaborative Fraud Intelligence Simulator",
        "version": "0.2.0",
        "docs": "/docs",
        "health": "/health",
    }
