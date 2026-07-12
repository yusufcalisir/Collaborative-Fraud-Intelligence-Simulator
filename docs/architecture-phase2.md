# Architecture & System Design: Phase 2 Collaborative AML Platform

This document describes the architectural additions and data flows introduced in Phase 2.

## Component Overview

Phase 2 builds upon the existing Federated Learning architecture, adding real-time alert processing, case management, entity resolution, and relationship graph analysis.

```mermaid
graph TD
    subgraph Presentation Layer
        UI[React Frontend / React Flow]
        WS[WebSocket Endpoint]
    end

    subgraph API & Orchestration Layer
        FastAPI[FastAPI Control Plane]
        AlertsR[Alerts Router]
        CasesR[Cases Router]
        EntitiesR[Entities Router]
        GraphR[Graph Router]
        ScenariosR[Scenarios Router]
        DashboardR[Dashboard Router]
        PredictR[Prediction Router]
    end

    subgraph Application & Business Logic
        RiskEng[Risk Scoring Engine]
        AlertSvc[Alert Intelligence Service]
        CaseSvc[Case Management Service]
        EntitySvc[Entity Resolution Service]
        GraphEng[Graph Engine]
        StreamEng[Streaming Engine]
    end

    subgraph Data & Storage Layer
        DB[(PostgreSQL Database)]
        Cache[(Redis Event Broker & Cache)]
    end

    UI --> FastAPI
    FastAPI --> AlertsR & CasesR & EntitiesR & GraphR & ScenariosR & DashboardR & PredictR
    WS --> StreamEng
    
    AlertsR --> AlertSvc
    PredictR --> AlertSvc
    CasesR --> CaseSvc
    EntitiesR --> EntitySvc
    GraphR --> GraphEng
    ScenariosR --> StreamEng
    DashboardR --> RiskEng

    AlertSvc --> RiskEng
    EntitySvc --> GraphEng
    StreamEng --> Cache
    Cache --> WS
    
    AlertSvc & CaseSvc & EntitySvc & GraphEng --> DB
```

---

## Data Flow: Real-time Replay and Detection

During scenario replay, events flow through the system as follows:

```
[Scenario Simulator]
        │
        ▼ (Streaming Event)
[Streaming Engine] ────(Pub/Sub)────► [Redis Channel] ────► [WebSocket] ────► [Frontend UI]
        │
        ▼ (Process Transaction)
[Risk Scoring Engine]
   ├── evaluates 9 signals (ML, Velocity, Country, etc.)
   └── returns Composite Risk Score (0-1000)
        │
        ▼ (If Risk Score > Threshold)
[Alert Intelligence Service]
   ├── Generates Alert Entity
   ├── Extracts PrivacyPreservingIdentifiers (HMAC-SHA256)
   └── Publishes SharedIntelligence indicator
        │
        ▼ (Trigger Resolution)
[Entity Resolution Service]
   ├── Maps privacy hashes across banks
   └── Identifies cross-institution overlaps
        │
        ▼ (Update Network Map)
[Graph Engine]
   ├── Registers resolved nodes & edges
   └── Detects suspicious graph clusters (Connected Components)
```

---

## Privacy-Preserving Mechanics

To satisfy strict data protection regulations (e.g., GDPR, CCPA, bank secrecy acts), the architecture enforces the following security boundaries:

1. **Zero Raw PII Transmission**:
   * No raw emails, telephone numbers, card numbers, or transaction IDs leave the bank.
   * All PII is converted to deterministic hashes locally at the bank level before any shared analysis.
2. **HMAC-SHA256 Deterministic Hashing**:
   * Hashes are computed using a secure keyed-hash message authentication code:
     $$\text{Privacy Hash} = \text{HMAC-SHA256}(\text{Shared Key}, \text{Entity Type} \mathbin{\Vert} \text{Raw Value})$$
   * Using a type-specific salt prevents cross-type rainbow table attacks.
   * The resulting hash is truncated to a readable size (16 characters) for display within the simulation.
3. **Federated Learning Alignment**:
   * Model weights are trained using local SGD and aggregated using secure Federated Averaging (FedAvg). This is combined with Phase 2's collaborative intelligence layer to protect transaction integrity at all execution stages.

---

## Design Patterns & Architectural Choices

* **Signal-Combiner Pattern**: The `RiskScoringEngine` decouples independent risk assessment strategies (ML, rules, baseline comparisons). This makes it easy to add or adjust weights without changing the scoring engine skeleton.
* **Separation of Concerns (Clean Architecture)**:
  * **Domain Layer** (dataclasses in `entities_phase2.py` and `value_objects_phase2.py`) is completely independent of frameworks.
  * **Application Layer** (services in `app/application/services`) handles core AML algorithms.
  * **Presentation Layer** (routers in `app/presentation/routers` and schemas in `app/application/schemas`) manages network endpoints and payloads.
* **Pub/Sub Scenario Replay**: Using Redis pub/sub decouples the simulation thread from FastAPI and WebSockets, ensuring smooth, low-latency UI updates during high-speed scenario runs.

---

## Distributed Federated Learning Engine (HTTP Engine)

When the federated learning engine is configured as `distributed` (e.g., `fl_engine_type = "distributed"`), the system transitions from an in-memory simulation to a realistic, distributed system design.

### Node Layout and Networking
* **Coordinator Node**: The central `fl-coordinator` container coordinates training rounds. It maintains global model parameters, schedules execution rounds, and triggers tasks.
* **Bank Client Nodes**: Bank clients (`bank-a`, `bank-b`, `bank-c`) run in their own container environments. They listen on designated HTTP ports (`8011`, `8012`, `8013`) and expose a dedicated client-serving API.

```mermaid
sequenceDiagram
    autonumber
    participant Coord as FL Coordinator
    participant BA as Bank Client A (bank-a:8011)
    participant BB as Bank Client B (bank-b:8012)
    participant BC as Bank Client C (bank-c:8013)

    Note over Coord, BC: 1. Initialization Phase
    Coord->>BA: POST /api/v1/bank-client/initialize
    BA-->>Coord: 200 OK (Dataset Initialized)
    Coord->>BB: POST /api/v1/bank-client/initialize
    BB-->>Coord: 200 OK
    Coord->>BC: POST /api/v1/bank-client/initialize
    BC-->>Coord: 200 OK

    loop Training Rounds (1 to N)
        Note over Coord, BC: 2. Local Training Phase
        Coord->>BA: POST /api/v1/bank-client/train (Global Model Weights)
        Coord->>BB: POST /api/v1/bank-client/train (Global Model Weights)
        Coord->>BC: POST /api/v1/bank-client/train (Global Model Weights)
        
        Note over BA: Train on Local Partition (SGD/DP)
        Note over BB: Train on Local Partition (SGD/DP)
        Note over BC: Train on Local Partition (SGD/DP)

        BA-->>Coord: 200 OK (Updated Weights + Samples Count + Local Loss)
        BB-->>Coord: 200 OK (Updated Weights + Samples Count + Local Loss)
        BC-->>Coord: 200 OK (Updated Weights + Samples Count + Local Loss)

        Note over Coord: 3. Secure Aggregation & Weight Update

        Note over Coord, BC: 4. Evaluation Phase
        Coord->>BA: POST /api/v1/bank-client/evaluate (Aggregated Weights)
        Coord->>BB: POST /api/v1/bank-client/evaluate (Aggregated Weights)
        Coord->>BC: POST /api/v1/bank-client/evaluate (Aggregated Weights)

        BA-->>Coord: 200 OK (Local Test Metrics)
        BB-->>Coord: 200 OK (Local Test Metrics)
        BC-->>Coord: 200 OK (Local Test Metrics)
    end
```

## Event-Driven Federated Learning Engine (Redis Pub/Sub Engine)

When the federated learning engine is configured as `event_driven` (e.g., `fl_engine_type = "event_driven"`), communication shifts from synchronous HTTP/REST to asynchronous event exchanges using a **Redis Pub/Sub Event Broker**.

### Security & Networking Advantages
* **Zero Inbound Port Exposure**: Bank client nodes (`bank-a`, `bank-b`, `bank-c`) do not open any inbound HTTP ports to the network. They connect to the Redis broker as outbound clients. This reflects enterprise financial networks where inbound HTTP traffic is restricted.
* **Loose Coupling**: The central coordinator and client nodes do not require IP/port routing tables or DNS mapping of participants.
* **Robust Correlation**: Transactions across rounds are tracked using unique message identifiers (`correlation_id`).

### Messaging Flow

```mermaid
sequenceDiagram
    autonumber
    participant Coord as FL Coordinator
    participant Broker as Redis Event Broker
    participant BA as Bank Client A (Outbound Consumer)

    Note over Coord, BA: 1. Initialization Phase
    Coord->>Broker: Publish: bank_client_bank_a_init (CorrelationID: init_123)
    Broker->>BA: Deliver event
    Note over BA: Generate Local Partition Dataset
    BA->>Broker: Publish: bank_client_bank_a_init_response (CorrelationID: init_123)
    Broker-->>Coord: Deliver event (Init Complete)

    loop Training Rounds (1 to N)
        Note over Coord, BA: 2. Local Training Phase
        Coord->>Broker: Publish: bank_client_bank_a_train (Global Weights, CorrelationID: train_1)
        Broker->>BA: Deliver event
        Note over BA: Train on Local Partition (SGD/DP)
        BA->>Broker: Publish: bank_client_bank_a_train_response (Updated Weights, CorrelationID: train_1)
        Broker-->>Coord: Deliver event

        Note over Coord: 3. Secure Aggregation & Weight Update

        Note over Coord, BA: 4. Evaluation Phase
        Coord->>Broker: Publish: bank_client_bank_a_evaluate (Aggregated Weights, CorrelationID: eval_1)
        Broker->>BA: Deliver event
        Note over BA: Evaluate on Local Test Data
        BA->>Broker: Publish: bank_client_bank_a_evaluate_response (Metrics, CorrelationID: eval_1)
        Broker-->>Coord: Deliver event
    end
```
