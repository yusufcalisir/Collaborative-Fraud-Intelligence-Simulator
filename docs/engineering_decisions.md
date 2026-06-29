# Engineering Decisions

> ADR-style decision log. Each entry documents what was decided, why, and what was traded off.

---

## ED-001: Custom FL Engine vs Flower (flwr)

**Date**: 2026-06-29
**Status**: Accepted

### Context

Flower (`flwr`) is the standard open-source framework for federated learning, providing gRPC-based client-server communication, strategy abstractions, and multi-machine deployment.

### Decision

Build a custom in-process FL engine instead of using Flower.

### Rationale

1. **Failure injection control**: We need deterministic dropout, reconnection, and latency simulation per round. Flower's client lifecycle is managed by the framework, making fine-grained failure injection harder.
2. **UI observability**: The simulator's value proposition is round-by-round progress visible in the dashboard. Our custom engine emits progress callbacks at every step.
3. **Single-process simulation**: All three "banks" run in the same process. Flower's architecture assumes separate client processes communicating over gRPC, which adds complexity without benefit for a simulator.
4. **Educational clarity**: The custom engine code is self-documenting — readers can follow the FedAvg algorithm step by step.

### Tradeoff

This engine **cannot** scale to distributed multi-machine deployment. In production, use Flower with gRPC for real cross-network federated learning. The README explicitly documents this distinction.

---

## ED-002: Synthetic Data vs Real Datasets

**Date**: 2026-06-29
**Status**: Accepted

### Context

Standard fraud datasets (IEEE-CIS, Kaggle Credit Card) exist but are single-institution and cannot demonstrate Non-IID effects.

### Decision

Generate synthetic Non-IID transaction data with three distinct bank profiles.

### Rationale

1. **Non-IID control**: We can precisely control fraud ratios, transaction patterns, and feature distributions per bank — the core of what makes FL interesting.
2. **Reproducibility**: Deterministic generation with fixed seeds means identical results across runs.
3. **No licensing**: No data distribution restrictions.
4. **Narrative**: Each bank has a named identity (Meridian National, Nexus Digital, Heritage Regional) with distinct fraud patterns that tell a story.

### Tradeoff

Synthetic data lacks the complexity of real financial transactions. Feature engineering is simplified. In production, the same FL pipeline would work with real data.

---

## ED-003: SQLAlchemy 2.0 Async + JSON Columns

**Date**: 2026-06-29
**Status**: Accepted

### Context

Simulation results include nested structures (per-bank metrics, per-round data, confusion matrices, ROC curves) that don't map cleanly to normalized relational tables.

### Decision

Use PostgreSQL JSON columns for denormalized storage of metrics, bank data, and round data.

### Rationale

1. **Schema flexibility**: Metrics structure evolves as we add new evaluation methods.
2. **Read optimization**: A single query returns the full simulation with all nested data.
3. **Development velocity**: No migration needed when adding a new metric field.
4. **Appropriate scale**: The simulator handles hundreds of simulations, not millions.

### Tradeoff

JSON columns lose referential integrity, are harder to query/index for analytics, and can't enforce schema constraints. At production scale, normalize metrics into separate tables with proper indexing.

---

## ED-004: Celery for Training Execution

**Date**: 2026-06-29
**Status**: Accepted

### Context

A federated training simulation with 10 rounds, 3 banks, 50K transactions per bank takes 1-5 minutes. This cannot block the FastAPI event loop.

### Decision

Dispatch simulations as Celery tasks with Redis as broker and result backend.

### Rationale

1. **Non-blocking API**: FastAPI returns 202 Accepted immediately.
2. **Progress tracking**: The Celery task pushes progress to Redis pub/sub.
3. **Retry/monitoring**: Celery provides built-in task tracking and Flower (the monitoring tool, not FL framework) for observability.
4. **Process isolation**: PyTorch training runs in a separate worker process.

### Tradeoff

Adds operational complexity (Redis + Celery worker processes). For a simpler deployment, could use FastAPI BackgroundTasks, but that runs in the same process and can't survive API restarts.

---

## ED-005: React Query Over Redux/Zustand for Server State

**Date**: 2026-06-29
**Status**: Accepted

### Context

The frontend primarily displays server-side data (simulation results, bank configs, training rounds).

### Decision

Use TanStack React Query for all server state. Zustand is a dependency but reserved for future client-only UI state.

### Rationale

1. **Auto-refetch**: Running simulations update automatically via polling intervals.
2. **Cache management**: Completed simulations are cached and don't re-fetch unnecessarily.
3. **Loading/error states**: Built-in, no boilerplate.
4. **Conditional polling**: Simulations auto-poll while running, stop when completed.

### Tradeoff

WebSocket integration requires manual event handling outside React Query. For the current scope, polling + WebSocket (when connected) provides sufficient real-time experience.

---

## ED-006: Simulated Privacy vs Cryptographic Implementations

**Date**: 2026-06-29
**Status**: Accepted

### Context

Real secure aggregation requires multi-party computation (MPC) protocols. Real differential privacy requires rigorous privacy accounting (Rényi DP).

### Decision

Implement conceptually correct but simplified versions:
- **Secure aggregation**: Pairwise masks that mathematically cancel during summation
- **Differential privacy**: Gaussian mechanism with basic sequential composition

### Rationale

1. **Mathematical correctness**: The masks do cancel. The noise calibration formula is correct.
2. **Educational value**: Readers can understand the principle without MPC library complexity.
3. **Verifiable**: Unit tests prove that masked aggregation produces identical results to plaintext.

### Tradeoff

Not production-grade. The threat model documents the gap between simulator and production security requirements. Production should use `opacus` for DP and PySyft/TF Encrypted for MPC.

---

## ED-007: Tailwind CSS v4 Over Vanilla CSS

**Date**: 2026-06-29
**Status**: Accepted

### Context

The frontend needs a dark-mode, glassmorphism-heavy design with custom theme tokens.

### Decision

Use Tailwind CSS v4 with `@theme` directive for custom design tokens, plus a small amount of custom CSS for glass effects and animations.

### Rationale

1. **Tailwind v4**: New CSS-first configuration (no `tailwind.config.js`), native `@theme` tokens.
2. **Utility-first**: Rapid iteration on component styling without context-switching to CSS files.
3. **Custom tokens**: `@theme` directive lets us define our own color system while keeping utility classes.

### Tradeoff

Larger initial learning curve for Tailwind v4 vs v3. The `@theme` API is relatively new. Custom CSS is still needed for glassmorphism effects.
