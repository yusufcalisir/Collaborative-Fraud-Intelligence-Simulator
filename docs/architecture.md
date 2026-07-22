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
*   `connectors/`: Production Bank Connector sub-system implementing Hexagonal Ports & Adapters:
    *   `base_connector.py`: Defines the `BaseBankConnector` abstract interface and unified `NormalizedTransaction` Pydantic domain schema.
    *   `streaming_connector.py`: High-throughput real-time payment event streaming connector for Kafka, RabbitMQ, and Redis streams.
    *   `iso20022_connector.py`: Financial message parser converting ISO 20022 MX (`pacs.008`, `pacs.009`) XML and SWIFT MT103/MT202 text records into normalized transactions.
    *   `batch_connector.py`: End-Of-Day (EOD) file batch parser for CSV and Parquet transaction dumps.
    *   `rest_connector.py`: HTTP REST adapter supporting mTLS, OAuth2, HMAC payload signing, and real-time webhook ingestion.
    *   `factory.py`: Configuration-driven `BankConnectorFactory` resolving per-bank connector implementations.
*   `security/smart_contract_driver.py`: Web3 & CBDC settlement driver executing automated token disbursements (`wCBDC`, `USDC`, `e-TRY`) on `ConsortiumIncentiveSettlement.sol` based on LOO Shapley values.
*   `grpc/`: High-Performance Bidirectional Streaming gRPC Transport Layer over HTTP/2 defined via `fl_service.proto` (`RegisterClient`, `Heartbeat` streaming, `StreamModelParameters` chunking, `DownloadGlobalModel` chunking).
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
### 3.3 High-Performance Bidirectional gRPC Transport Layer
```
[Bank Node Client] ──(HTTP/2 Channel)──► [gRPC Server (50051)] ──► [FederatedLearningServicer]
        │                                                                   │
        ├── 1. RegisterClient(bank_id, cert_fp) ──────────────────────────► session_token & cluster_id
        ├── 2. Heartbeat(stream ClientHeartbeat) ◄──(Bidirectional)───────► stream CoordinatorStatus
        ├── 3. StreamModelParameters(stream ParameterChunk) ──────────────► Reassemble & Validate Payload
        └── 4. DownloadGlobalModel(ModelDownloadRequest) ◄──(Server Stream)── stream ModelChunk (SHA-256)
```

The gRPC transport layer handles high-throughput, low-latency node communications using Protocol Buffers (`cfi.fl.v1.FederatedLearningService`):
1. **Node Registration (`RegisterClient`):** Validates bank certificate fingerprints and returns a session token and assigned cluster ID.
2. **Bidirectional Heartbeat (`Heartbeat`):** Streams client telemetry (CPU, memory, dataset size) while receiving coordinator state commands (`IDLE`, `START_TRAINING`, `CANCEL_ROUND`, `UPDATE_CONFIG`).
3. **Client-Streaming Parameters (`StreamModelParameters`):** Transmits encrypted model updates split into 1 KB binary chunks signed with digital signatures.
4. **Server-Streaming Global Model (`DownloadGlobalModel`):** Delivers aggregated global model weights in SHA-256 checksum-verified binary chunks.

---

## 4. Analytical Drift Detection Suite

We implement dynamic, multi-pair statistical checks inside `presentation/routers/banks.py`:

1.  **Jensen-Shannon (JS) Divergence:** Measures categorical and continuous feature probability divergence:
    $$D_{\text{JS}}(P \parallel Q) = \frac{1}{2} D_{\text{KL}}(P \parallel M) + \frac{1}{2} D_{\text{KL}}(Q \parallel M)$$
    where $M = \frac{1}{2}(P + Q)$, using base-2 logarithm to bound outcomes in $[0, 1]$.
2.  **Population Stability Index (PSI):** Measures feature shifts across dynamic decile bins:
    $$\text{PSI} = \sum_{b=1}^{B} (A_b - E_b) \times \ln\left(\frac{A_b}{E_b}\right)$$
3.  **Concept Drift:** Evaluates $P(Y \mid X)$ stability by training a logistic regression model on Bank A and calculating the prediction shift on Bank B, paired with segment-specific conditional JS drifts.

### 4.1 Asynchronous Background Retraining Pipeline
Model retraining is decoupled from manual tick loops into an automated, asynchronous Celery worker task (`execute_automated_retraining_task` in `backend/app/tasks/simulation_tasks.py`):
1. **Trigger Criteria (`RetrainingTriggerEngine`)**:
   - **Data Ingestion Threshold**: Triggers when new normalized transactions reach target batch volume ($\ge 50,000$ records).
   - **Drift Detection Trigger**: Triggers when Population Stability Index ($\text{PSI} > 0.20$) or Kolmogorov-Smirnov test ($p < 0.05$) indicates significant feature/concept drift.
   - **Scheduled Consortium Cadence**: Periodic cron trigger for scheduled federated rounds.
2. **Worker Execution Pipeline**:
   - Local Celery worker fetches normalized training batch from `StreamingFeatureStore`.
   - Executes PyTorch model training loop with Opacus Differential Privacy (DP-SGD) noise injection (`add_noise_to_weights`).
   - Evaluates candidate model accuracy and ROC-AUC quality gate ($\text{ROC-AUC} > 0.70$).
   - Compresses encrypted parameter update payload (Zstandard) and queues it for gRPC transmission to central coordinator.

---

## 5. Cryptographic Parameter Exchange Pipeline

The parameter exchange pipeline (`backend/app/infrastructure/security/secure_parameter_pipeline.py`) enforces a 7-step cryptographic transmission sequence to protect local model updates against gradient inversion attacks, model poisoning, and network interception:

1. **Gradient Calculation ($\Delta w$)**: Computes parameter deltas relative to current global model weights.
2. **Gradient Sparsification & Compression (`compression_engine.py`)**: Applies Top-K sparsification (retaining top K% highest magnitude gradient elements) and Zstandard/zlib lossless payload compression to reduce bandwidth footprint.
3. **Differential Privacy Injection (`privacy_service.py`)**: Inject calibrated Gaussian noise via Opacus DP-SGD ($\epsilon, \delta$) with clipping bounds.
4. **Cryptographic Masking (`fhe_driver.py` / SecAgg)**: Applies pairwise zero-sum SecAgg masks or FHE CKKS ciphertext vectors.
5. **Digital Envelope Signing (`signature_verifier.py`)**: Signs compressed payload using 4096-bit RSA-PSS or Ed25519 private keys (`DigitalEnvelopeSigner`).
6. **gRPC Delivery over mTLS 1.3 (`fl_service.proto`)**: Streams signed parameter chunks over outbound mutual TLS 1.3 channels to central coordinator.
7. **Signature Verification & Byzantine Aggregation (`signature_verifier.py`)**: Central coordinator verifies digital signature against Vault PKI public keys (`SignatureVerifier`), rejects tampered payloads, applies Byzantine defense (Krum / Coordinate-wise Median), and aggregates global model weights.

---

## 6. High-Availability & Asynchronous Fault Tolerance

Prevents training round deadlocks caused by bank node network outages, maintenance windows, or latency spikes.

### 6.1 Asynchronous Federated Aggregation (`async_fl_engine.py`)

The `AsyncFLEngine` implements the **FedAsync** parameter update protocol. Fast bank nodes submit model updates immediately — without blocking on straggler nodes — using a staleness attenuation factor to preserve convergence quality.

**Staleness Attenuation Function:**

$$S(\tau) = (1 + \tau)^{-\alpha}$$

where $\tau = t_{\text{current}} - t_{\text{submitted}}$ (rounds elapsed since submission) and $\alpha$ is the attenuation exponent (default: $\alpha = 0.5$).

**Global Weight Update Rule:**

$$W^{(t+1)} = (1 - \alpha_\tau)\,W^{(t)} + \alpha_\tau\,W_i^{(t-\tau)}$$

where $\alpha_\tau = \eta \cdot S(\tau)$ is the learning rate weighted by staleness attenuation. Fresh updates ($\tau = 0$) receive full learning rate weight ($S(0) = 1.0$); older stale updates are progressively down-weighted.

### 6.2 Dynamic Quorum Timeout Manager (`quorum_manager.py`)

The `DynamicQuorumManager` monitors real-time round submission progress across all registered bank nodes. It automatically triggers round aggregation as soon as the minimum quorum threshold is satisfied — without waiting for the target window to expire.

**Quorum States:**

| State | Condition |
| :--- | :--- |
| `WAITING` | Submitted nodes / Registered nodes < 60% and elapsed < 300s |
| `QUORUM_REACHED` | Submitted nodes / Registered nodes ≥ 60% |
| `TIMEOUT_EXPIRED` | Elapsed time ≥ 300s before quorum threshold reached |

**Auto-Aggregation Protocol:**
1. Bank nodes register for the round via `register_nodes(node_ids)`.
2. Each gradient/weight submission is recorded via `record_node_submission(node_id)`.
3. After each submission, `evaluate_quorum_status()` checks: $\frac{|\text{submitted}|}{|\text{registered}|} \ge 0.60$.
4. If `QUORUM_REACHED` → immediate aggregation trigger (no timeout wait).
5. If `TIMEOUT_EXPIRED` → graceful fallback with partial aggregation from submitted nodes.

---

## 7. Spectral Anomaly Detection & Backdoor Poisoning Defense (`spectral_defense.py`)

### 7.1 Threat Model

Targeted backdoor attacks attempt to inject a **low-rank gradient perturbation** into the federated aggregation process — malicious bank nodes submit parameter updates that are indistinguishable from legitimate updates in L2 norm, but align along a shared stealthy subspace designed to bypass fraud detection for specific money mule accounts.

### 7.2 SVD Spectral Projection Algorithm

The `SpectralAnomalyDetector` applies Singular Value Decomposition to the stacked gradient matrix $G \in \mathbb{R}^{K \times d}$ (K clients, d parameters) before aggregation:

**Step 1 — Stack gradient matrix:**
$$G = \begin{bmatrix} \Delta w_1^T \\ \Delta w_2^T \\ \vdots \\ \Delta w_K^T \end{bmatrix}$$

**Step 2 — Compute dominant right singular vector via power iteration:**
$$G = U \Sigma V^T \quad \Rightarrow \quad v_1 = \arg\max_{‖v‖=1} ‖Gv‖$$

**Step 3 — Compute per-client spectral projection scores:**
$$s_i = |\langle \Delta w_i, v_1 \rangle|^2$$

Backdoor-poisoned updates inject a dominant low-rank perturbation that results in disproportionately large $s_i$ values, separating malicious clients from the honest majority.

**Step 4 — Threshold detection:**
$$\theta = \mu_s + \tau \cdot \sigma_s$$
$$\text{quarantine}(i) \iff s_i > \theta$$

where $\tau$ = `spectral_threshold_multiplier` (default: 1.5), $\mu_s$ = mean score, $\sigma_s$ = standard deviation.

### 7.3 Robust Spectral Aggregation

After quarantining poisoned nodes, the `aggregate_robust_spectral()` method computes a clean parameter average over the honest subset $\mathcal{H} = \{i : s_i \le \theta\}$:

$$w^{(t+1)}_{\text{global}} = \frac{1}{|\mathcal{H}|} \sum_{i \in \mathcal{H}} \Delta w_i$$

### 7.4 Implementation Details

| Component | Module | Purpose |
| :--- | :--- | :--- |
| `SpectralDefenseConfig` | `spectral_defense.py` | Config: threshold multiplier τ, min_clients |
| `SpectralAnomalyReport` | `spectral_defense.py` | Per-client spectral score & quarantine status |
| `SpectralAnomalyDetector` | `spectral_defense.py` | SVD power iteration + anomaly detection + robust aggregation |
| `_power_iteration()` | `spectral_defense.py` | Pure-stdlib dominant right singular vector $v_1$ computation |

> **Pure stdlib implementation**: The spectral defense module uses only Python stdlib (`math`, `dataclasses`) — no numpy or scipy dependency required — maintaining clean domain layer isolation.

---

## 8. Technology Stack & Directory Structure

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

