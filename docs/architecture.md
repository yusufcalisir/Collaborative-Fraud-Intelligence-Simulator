# Clean Architecture & System Design

## 1. Architectural Overview

The Collaborative Fraud Intelligence (CFI) Simulator is designed around **Clean Architecture** (Ports & Adapters / Hexagonal Architecture) principles. It isolates core domain logic from framework, presentation, database, and telemetry concerns. Dependencies flow strictly **inward** toward the Domain layer.

The platform operates in two deployment modes dynamically configured by the `microservice_mode` configuration setting:
1.  **Monolithic Mode:** Services run inside a single FastAPI control plane, communicating via direct in-process function calls.
2.  **Microservices Mode:** The system is decomposed into 4 independent, stateless processes orchestrated via Docker Compose:
    *   **`gateway`:** API entry point implementing rate-limiting, authentication, logging, and down-stream routing.
    *   **`fl-coordinator`:** Manages the federated learning loops, client drops, secure aggregation, and Ray/Flower integrations.
    *   **`identity-graph`:** Performs deterministic HMAC-SHA256 entity resolution and builds React Flow-compatible network maps.
    *   **`fraud-alert`:** Executes the 9-Signal Risk Scoring Engine and handles case management flows.

```
       [ Presentation Layer ] (FastAPI Routers, WebSockets, React UI)
                 │
                 ▼
       [ Application Layer ] (Services, Orchestrators, Use Cases)
                 │
        ┌────────┴────────┐
        ▼                 ▼
  [ Domain Layer ]  [ Infrastructure Layer ] (ORM, Redis, Celery, Telemetry)
```

---

## 2. Layer Responsibilities

### 2.1 Domain Layer (`backend/app/domain/`)
The core domain model, written in pure Python. It contains business definitions, structures, and value objects. It remains completely independent of FastAPI, Pydantic, SQLAlchemy, or PyTorch.

*   `enums.py`: Enumerations for FL Engine types, Privacy mechanisms, Client status, and Bank tiers.
*   `entities.py` & `entities_phase2.py`: Entities with active identity (`Bank`, `SimulationRun`, `TrainingRound`, `Alert`, `Case`, `ResolvedEntity`).
*   `value_objects.py` & `value_objects_phase2.py`: Immutable data structures (`ModelWeights`, `EvaluationMetrics`, `RiskSignal`, `GraphNode`, `GraphEdge`).

### 2.2 Application Layer (`backend/app/application/`)
Contains business logic orchestration. Defines ports (interfaces) for data access, which are implemented by the infrastructure layer.

*   `services/fl_engine.py`: Implements parameter aggregation (FedAvg, coordinate median, Krum) and secure aggregation masking.
*   `services/model_service.py`: Lifecycle of the PyTorch MLP model (training, CPU/GPU evaluation, Integrated Gradients attributions).
*   `services/privacy_service.py`: Bounded L2 gradient clipping and Gaussian mechanism noise addition.
*   `services/risk_engine.py`: Combines 9 independent heuristic and ML signals into a single score ($0 \text{ to } 1000$).
*   `services/entity_resolution.py`: Computes deterministic one-way HMAC-SHA256 privacy hashes for account and device identifiers.
*   `services/explainability_service.py`: Computes SHAP attributions using `shap.KernelExplainer` with analytical fallbacks.
*   `services/model_registry.py`: Manifest-backed model repository managing versioning, active symlinks, and Canary Gates.

### 2.3 Infrastructure Layer (`backend/app/infrastructure/`)
Concrete implementation of dependencies. Adapts foreign libraries and databases.

*   `database.py` & `models.py`: SQLAlchemy 2.0 async engine and relational database tables.
*   `redis_store.py`: A fault-tolerant state manager. It synchronizes simulation configurations and round metrics to Redis. If Redis is unreachable, it falls back to a thread-safe, in-memory cache to maintain liveness.
*   `telemetry.py`: Bypasses metrics or mounts a `/metrics` ASGI app for Prometheus based on configurations.
*   `celery_app.py`: Background worker queue for handling long-running PyTorch training loops without blocking FastAPI.

### 2.4 Presentation Layer (`backend/app/presentation/`)
Interactions with clients.
*   `routers/*.py`: FastAPI REST API endpoints verifying request formats via Pydantic schemas.
*   `websockets/*.py`: Persistent WebSocket connections sending training round progress and scenario replay events.

---

## 3. Data Flow & Mechanics

### 3.1 Federated Training Cycle
```
[React UI] ──(Start)──► [Gateway] ──► [Simulation Tasks (Celery)]
                                             │
   ┌─────────────────────────────────────────┘
   ▼
[fl-coordinator]
   ├── 1. Generate Non-IID bank datasets
   ├── 2. For round r = 1..R:
   │     ├── Apply client availability (dropout probability)
   │     ├── Client local SGD training (ModelService.train_local)
   │     ├── If DP: PrivacyService.clip_model_update + add_noise_to_weights
   │     ├── If SecAgg: apply_secure_aggregation_masks
   │     └── Aggregate parameters (FedAvg, Median, or Krum)
   ├── 3. Evaluate candidate model on holdout validation data
   └── 4. Promote candidate if AUC >= Active AUC - 0.005 (Canary Gate)
```

### 3.2 Real-Time Collaborative AML Screening
```
[Transaction Event] ──► [fraud-alert Service]
                                │
                                ▼
                    [Risk Scoring Engine] (9 Signals)
                                │
                                ▼ (If Score >= 600)
                     [Alert Generated] ──(HMAC-SHA256)──► [identity-graph]
                                                                │
                                                                ▼
                                                      [Entity Resolution]
                                                                │
                                                                ▼
                                                        [React Flow Map]
```

---

## 4. Analytical Drift Detection Suite

We implement dynamic, multi-pair statistical checks inside `presentation/routers/banks.py`:

1.  **Jensen-Shannon (JS) Divergence:** Measures categorical and continuous feature probability divergence:
    $$D_{\text{JS}}(P \parallel Q) = \frac{1}{2} D_{\text{KL}}(P \parallel M) + \frac{1}{2} D_{\text{KL}}(Q \parallel M)$$
    where $M = \frac{1}{2}(P + Q)$, using base-2 logarithm to bound outcomes in $[0, 1]$.
2.  **Population Stability Index (PSI):** Measures feature shifts across dynamic decile bins:
    $$\text{PSI} = \sum_{b=1}^{B} (A_b - E_b) \times \ln\left(\frac{A_b}{E_b}\right)$$
3.  **Concept Drift:** Evaluates $P(Y \mid X)$ stability by training a logistic regression model on Bank A and calculating the prediction shift on Bank B, paired with segment-specific conditional JS drifts.

---

## 5. Technology Stack & Directory Structure

```
├── backend/
│   ├── app/
│   │   ├── domain/               # Domain Value Objects & Entities
│   │   ├── application/          # Service Layer (Business Logic)
│   │   ├── infrastructure/       # Database, Redis, Celery, Telemetry
│   │   └── presentation/         # API Controllers & WebSocket handlers
│   └── tests/                    # Unit, Integration, & Property-Based suites
├── frontend/
│   ├── src/
│   │   ├── api/                  # REST client and Query hooks
│   │   ├── components/           # Reusable Layouts, Dashboards, Charts
│   │   └── pages/                # Views (Dashboard, Alerts, Registry, Graph)
│   └── package.json
└── docs/                         # Security & System Design documentation
```
