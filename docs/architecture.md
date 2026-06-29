# Architecture

## Overview

The Collaborative Fraud Intelligence Simulator follows **Clean Architecture** (Ports & Adapters), enforcing strict separation between business logic, application orchestration, infrastructure concerns, and API presentation.

```
Presentation → Application → Domain
                   ↑
            Infrastructure
```

Dependencies flow **inward**. The Domain layer has zero external dependencies. The Application layer defines interfaces (ports) that the Infrastructure layer implements (adapters).

---

## Layer Responsibilities

### 1. Domain Layer (`app/domain/`)

The innermost layer. Contains pure business concepts with no framework imports.

| Component | File | Purpose |
|-----------|------|---------|
| **Entities** | `entities.py` | `Bank`, `SimulationRun`, `TrainingRound` — core business objects with identity |
| **Value Objects** | `value_objects.py` | `ModelWeights`, `EvaluationMetrics`, `SimulationConfig`, `BankDataProfile` — immutable data carriers |
| **Enums** | `enums.py` | `SimulationStatus`, `BankTier`, `ClientStatus`, `PrivacyMechanism`, `AggregationMethod` |

**Key constraint**: No SQLAlchemy, no Pydantic, no FastAPI imports. Only Python stdlib + `dataclasses`.

### 2. Application Layer (`app/application/`)

Contains business logic orchestration and service definitions.

| Component | File | Purpose |
|-----------|------|---------|
| **SimulationService** | `services/simulation_service.py` | Orchestrates the full FL pipeline: data generation → local training → federated training → evaluation |
| **FederatedLearningEngine** | `services/fl_engine.py` | FedAvg aggregation, client availability simulation, secure aggregation masks |
| **ModelService** | `services/model_service.py` | PyTorch model lifecycle: create, train, evaluate, parameter exchange |
| **PrivacyService** | `services/privacy_service.py` | Differential privacy noise, gradient clipping, budget tracking |
| **DataGenerator** | `services/data_generator.py` | Non-IID synthetic transaction data with 3 distinct bank profiles |
| **MetricsService** | `services/metrics_service.py` | Converts eval dicts to domain value objects, computes aggregate comparisons |
| **Schemas** | `schemas/simulation.py` | Pydantic models for API request/response validation |
| **Interfaces** | `interfaces/repositories.py` | Abstract repository contracts (ports) |

### 3. Infrastructure Layer (`app/infrastructure/`)

Implements application interfaces with concrete technologies.

| Component | File | Purpose |
|-----------|------|---------|
| **Database** | `database.py` | SQLAlchemy 2.0 async engine, session factory |
| **ORM Models** | `models.py` | `SimulationRunModel`, `BankConfigModel`, `TrainingRoundModel` |
| **Repositories** | `repositories/*.py` | Concrete implementations of repository interfaces |
| **Cache** | `cache.py` | Redis client for progress caching and pub/sub |
| **Celery App** | `celery_app.py` | Celery configuration with Redis broker |

### 4. Presentation Layer (`app/presentation/`)

HTTP/WebSocket interface.

| Component | File | Purpose |
|-----------|------|---------|
| **Simulation Router** | `routers/simulation.py` | CRUD endpoints + Celery task dispatch |
| **Banks Router** | `routers/banks.py` | Bank reference data |
| **Training Router** | `routers/training.py` | Per-round training data from Redis |
| **Health Router** | `routers/health.py` | Liveness + readiness probes |
| **WebSocket** | `websockets/training_ws.py` | Real-time training progress via Redis pub/sub |

---

## Data Flow

### Simulation Lifecycle

```
User → POST /api/v1/simulations
         │
         ▼
    SimulationRouter
         │ dispatch
         ▼
    Celery Task (run_simulation_task)
         │
         ▼
    SimulationService.run_simulation()
         │
         ├── Phase 1: DataGenerator.generate_bank_datasets()
         │     └── 3 Non-IID datasets (different fraud profiles)
         │
         ├── Phase 2: ModelService.train_local() × 3 banks
         │     └── Local-only baselines for comparison
         │
         ├── Phase 3: FederatedLearningEngine (N rounds)
         │     ├── For each round:
         │     │   ├── simulate_client_availability()
         │     │   ├── ModelService.train_local() per client
         │     │   ├── PrivacyService.clip + add_noise (if DP)
         │     │   ├── apply_secure_aggregation_masks (if SA)
         │     │   └── aggregate_parameters (FedAvg)
         │     └── Progress → Redis pub/sub → WebSocket → UI
         │
         └── Phase 4: ModelService.evaluate() × 3 banks
               └── Federated model tested on each bank's data
```

### Real-time Progress Flow

```
Celery Worker                Redis                WebSocket               React UI
     │                         │                      │                      │
     │── publish event ──────▶│                      │                      │
     │                         │── channel msg ─────▶│                      │
     │                         │                      │── send_text ───────▶│
     │                         │                      │                      │── update state
     │                         │                      │                      │── re-render
```

---

## Concurrency Model

| Concern | Solution |
|---------|----------|
| API request handling | FastAPI (async, uvicorn) |
| Heavy ML training | Celery workers (sync, separate process) |
| Progress notifications | Redis pub/sub → async WebSocket |
| Database I/O | SQLAlchemy 2.0 async (asyncpg) |
| Cache reads | redis.asyncio |

The API process **never blocks** on training. Celery workers run synchronously (PyTorch doesn't benefit from async) and push progress updates through Redis.

---

## Frontend Architecture

```
src/
├── api/             # API client, React Query hooks, TypeScript types
├── components/
│   ├── layout/      # Layout, Sidebar, Header
│   ├── dashboard/   # BankCard, SimulationControls, TrainingTimeline, MetricsComparison
│   └── charts/      # LossChart, ROCCurve, ConfusionMatrix, FeatureImportance, MetricsRadar
├── pages/           # Dashboard, SimulationView
└── utils/           # Formatters, constants
```

**State management**: React Query for server state (auto-refetch, caching). No client-side state management needed beyond local component state.

**Chart library**: Recharts — composable, React-native, supports responsive containers.
