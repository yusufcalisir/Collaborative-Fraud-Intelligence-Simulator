# System Design

> This document presents the system design as if answering a system design interview question: *"Design a privacy-preserving fraud detection system where multiple banks collaborate without sharing data."*

---

## 1. Requirements

### Functional

- Three independent banks want to improve fraud detection
- Banks cannot share raw transaction data (regulatory constraint)
- System should demonstrate measurable improvement from collaboration
- Real-time visibility into training progress
- Support for privacy-enhancing technologies (DP, secure aggregation)
- Resilience to client failures during training

### Non-Functional

- **Privacy**: No raw data leaves the bank boundary. Only model updates (gradients) are shared.
- **Correctness**: FedAvg aggregation produces a valid global model.
- **Observability**: Every round's metrics are tracked and visualized.
- **Reproducibility**: Deterministic with fixed random seeds.
- **Extensibility**: Adding new aggregation methods, privacy mechanisms, or banks should require minimal changes.

---

## 2. High-Level Design

```
                    ┌─────────────────────┐
                    │   Central Server    │
                    │   (Aggregator)      │
                    │                     │
                    │  ┌───────────────┐  │
                    │  │ Global Model  │  │
                    │  └───────┬───────┘  │
                    │          │          │
                    └──────────┼──────────┘
                   ┌───────────┼───────────┐
                   │           │           │
            ┌──────▼──┐  ┌────▼─────┐  ┌──▼───────┐
            │ Bank A  │  │  Bank B  │  │  Bank C  │
            │         │  │          │  │          │
            │ Local   │  │ Local    │  │ Local    │
            │ Data +  │  │ Data +   │  │ Data +   │
            │ Model   │  │ Model    │  │ Model    │
            └─────────┘  └──────────┘  └──────────┘

    Round Protocol:
    1. Server sends global model weights → each bank
    2. Each bank trains locally on its own data
    3. Each bank sends updated weights → server
    4. Server aggregates weights (FedAvg)
    5. Repeat for N rounds
```

In production, each "bank" would be a separate machine. In this simulator, all three are logical partitions running in the same process, which lets us:

- Control data generation with Non-IID profiles
- Inject failures deterministically
- Compare local vs federated models with the same test data

---

## 3. Core Components

### 3.1 Data Generation (Non-IID)

Real banks have **non-identically distributed** data. We simulate three distinct fraud profiles:

| Bank | Size | Fraud Rate | Pattern |
|------|------|-----------|---------|
| Meridian National (Large) | 50K txns | 0.8% | Velocity spikes, late-night hours |
| Nexus Digital (Medium) | 30K txns | 2.5% | New accounts, international transfers |
| Heritage Regional (Small) | 20K txns | 1.2% | Card testing, small-then-large amounts |

This Non-IID distribution is critical — it's what makes federated learning interesting. If all banks had identical data distributions, there'd be no collaborative advantage.

### 3.2 Model Architecture

**Fraud Detection MLP** (Multi-Layer Perceptron):

```
Input (10 features)
    │
    ▼
Linear(10, 64) → BatchNorm → ReLU → Dropout(0.3)
    │
    ▼
Linear(64, 32) → BatchNorm → ReLU → Dropout(0.2)
    │
    ▼
Linear(32, 1) → Sigmoid
    │
    ▼
Output (fraud probability)
```

10 input features: `amount`, `hour`, `day_of_week`, `merchant_category`, `channel`, `country`, `account_age_days`, `is_international`, `velocity_1h`, `amount_to_mean_ratio`.

### 3.3 Federated Averaging (FedAvg)

```
                     n_k
    w_global = Σ  ───── · w_k
               k    N

    where:
    - w_k = weights from bank k
    - n_k = number of training samples at bank k
    - N   = total training samples across all banks
```

Weighted averaging ensures banks with more data have proportionally more influence — appropriate because more data generally means more representative gradients.

### 3.4 Privacy Mechanisms

**Differential Privacy**:
- Gradient clipping: `||Δw|| ≤ C` (L2 norm bound)
- Gaussian noise: `N(0, σ²)` where `σ = C · √(2 ln(1.25/δ)) / ε`
- Budget tracking: cumulative ε across rounds

**Secure Aggregation** (simulated):
- Pairwise random masks `r_{ij}` generated between each client pair
- Bank i adds `r_{ij}`, Bank j subtracts `r_{ij}` → masks cancel during summation
- Server sees only the aggregate, not individual updates

### 3.5 Failure Injection

- **Client dropout**: Banks randomly go offline with configurable probability
- **Reconnection**: Previously dropped banks can rejoin (~70% probability)
- **Minimum quorum**: Training round requires minimum N clients (default 2/3)
- **Graceful degradation**: Rounds with insufficient clients are skipped, not failed

---

## 4. Scale Considerations

This is a simulator, but the design anticipates production scaling:

| Concern | Simulator | Production |
|---------|-----------|------------|
| Training execution | Single Celery worker | Multiple GPU workers |
| Client communication | In-process function calls | gRPC (Flower/flwr framework) |
| Aggregation | NumPy in-memory | Distributed parameter server |
| Model size | ~5K parameters (MLP) | Millions (transformer-based) |
| Data volume | 100K synthetic txns | Billions of real txns |
| Rounds | 10-100 | 100-1000 |
| Secure aggregation | Pairwise mask simulation | SMPC protocols (SPDZ, ABY3) |

---

## 5. Data Model

```
SimulationRun
  ├── id (UUID)
  ├── status (enum)
  ├── config (JSON)
  ├── banks_data (JSON — denormalized)
  └── rounds_data (JSON)

BankConfig
  ├── simulation_id (FK)
  ├── name, tier, fraud_ratio
  ├── local_metrics (JSON)
  └── federated_metrics (JSON)

TrainingRound
  ├── simulation_id (FK)
  ├── round_number
  ├── global_loss
  ├── participating_bank_ids
  ├── dropped_bank_ids
  └── timing data
```

Metrics are stored as JSON columns for flexibility. In a production system with millions of simulations, these would be normalized into separate metric tables with proper indexing.

---

## 6. API Design

RESTful API with WebSocket for real-time updates:

- `POST /simulations` → 202 Accepted (returns task ID)
- `GET /simulations/{id}` → Full simulation state
- `GET /simulations/{id}/comparison` → Local vs federated metrics
- `WS /ws/training/{id}` → Real-time round events

The 202 pattern is important — training can take minutes. The client polls or connects via WebSocket for progress.
