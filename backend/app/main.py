"""FastAPI application entry point.

Wires together all routers, middleware, and lifecycle hooks.
"""

from __future__ import annotations

import logging
import os

# Limit CPU threading for PyTorch, NumPy, OpenBLAS, MKL to prevent CPU starvation on low-spec servers
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

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
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown hooks."""
    logger.info("Starting Collaborative Fraud Intelligence Simulator")
    logger.info("Environment: %s", settings.app_env)

    # Ensure PyTorch threading limits are applied at runtime
    import torch

    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)

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
