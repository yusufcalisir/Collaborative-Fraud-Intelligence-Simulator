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

## Privacy-Preserving Graph Intelligence

Phase 2 introduces **Privacy-Preserving Entity Resolution (PSI)** and **Graph-Based Fraud Detection (Graph Analytics)**. These components operate jointly to match entities securely across banks and propagate threat risks over the transaction graph.

### 1. Diffie-Hellman Private Set Intersection (DH-PSI)

To match customers, cards, or device IDs without disclosing raw identifiers of non-overlapping records, we implement a commutative modular exponentiation protocol (DH-PSI):

1. **Parameters**: A shared 512-bit modular prime $p$ and a generator $g$.
2. **Local Keys**: Bank A generates private scalar key $a$; Bank B generates private scalar key $b$.
3. **Pass 1**:
   - Bank A encrypts its set of hashes $X_A$: $Y_A = \{ x^a \pmod p \mid x \in X_A \}$.
   - Bank B encrypts its set of hashes $X_B$: $Y_B = \{ x^b \pmod p \mid x \in X_B \}$.
   - They exchange their encrypted sets.
4. **Pass 2**:
   - Bank A encrypts Bank B's set: $Z_B = \{ y^a \pmod p \mid y \in Y_B \} = \{ x^{ab} \pmod p \}$.
   - Bank B encrypts Bank A's set: $Z_A = \{ y^b \pmod p \mid y \in Y_A \} = \{ x^{ba} \pmod p \}$.
5. **Intersection**: Since modular exponentiation is commutative ($x^{ab} \equiv x^{ba} \pmod p$), matching elements in $Z_A$ and $Z_B$ reveal the shared entities without exposing any other values.

```mermaid
sequenceDiagram
    autonumber
    participant BA as Bank Client A
    participant BB as Bank Client B
    Note over BA, BB: Pass 1: Local Encryption
    Note over BA: Encrypts set with private key 'a'
    Note over BB: Encrypts set with private key 'b'
    BA->>BB: Send A's encrypted set
    BB->>BA: Send B's encrypted set
    Note over BA, BB: Pass 2: Commutative Cross-Encryption
    Note over BA: Encrypts received set with key 'a'
    Note over BB: Encrypts received set with key 'b'
    BA->>BB: Send double-encrypted set (Z_B)
    BB->>BA: Send double-encrypted set (Z_A)
    Note over BA: Computes Z_A & Z_B intersection -> Matches
```

### 1.1 Fuzzy & Probabilistic Private Entity Resolution (LSH / Fuzzy PSI)

> **Status: ✅ Implemented** — `backend/app/domain/value_objects_phase2.py`, `backend/app/application/services/entity_resolution.py`, `backend/app/application/services/psi_service.py`, `frontend/src/pages/PsiPage.tsx`

Deterministic exact-string matching fails when bank records differ slightly in spelling, accents, or formatting (e.g., "Yusuf Çalışır" vs "Yusuf Calisir"). Phase 2 implements a three-stage privacy-preserving fuzzy entity matching pipeline:

#### Stage 1 — Standardization Pipeline (`standardize_input()`)

`value_objects_phase2.py :: standardize_input(raw_value, entity_type)` applies a pre-hashing normalization pipeline to all entity identifiers before any matching is attempted:

| Entity Type | Transformation Applied |
| :--- | :--- |
| `customer` / `merchant` | Unicode NFC → Turkish character transliteration (`ı→i`, `ş→s`, `ç→c`, `ğ→g`, `ö→o`, `ü→u`, `ß→ss`) → NFD accent stripping → lowercase → strip non-alphanumeric → collapse whitespace |
| `phone` | Extract all digit characters; if original input starts with `+`, preserve `+` prefix (E.164 format) |
| `email` | Strip surrounding whitespace → lowercase |
| `device` / others | Strip → lowercase |

This ensures that `"Yusuf Çalışır"` and `"Yusuf Calisir"` both standardize to `"yusuf calisir"` before any hash is computed.

#### Stage 2 — Locality-Sensitive Hashing (LSH) on Character n-grams (`compute_minhash_signature()`)

`value_objects_phase2.py :: compute_minhash_signature(text, num_hashes=16)` generates a compact probabilistic fingerprint:

1. **3-gram Extraction**: The standardized name is decomposed into a set of overlapping character 3-grams:
   $$S = \{ \text{text}[i:i+3] \mid 0 \le i \le \text{len(text)} - 3 \}$$
   e.g., `"yusuf calisir"` → `{"yus", "usu", "suf", "uf ", ...}`

2. **MinHash Signature**: $H=16$ independent hash seeds $i$ are applied to each shingle $s$ using a deterministic polynomial rolling hash modulo a large prime $M$:
   $$\text{sig}[i] = \min_{s \in S} \left( \left( (a_i \cdot h(s) + b_i) \bmod M \right) \right)$$

3. **Jaccard Approximation**: Similarity between two signatures is estimated as the fraction of matching positions:
   $$\widehat{J}(S_1, S_2) = \frac{|\{ i \mid \text{sig}_1[i] = \text{sig}_2[i] \}|}{H}$$

The 16-dimensional MinHash vector is stored directly in the entity's `attributes["minhash_signature"]` field, eliminating the need for a separate LSH index store.

#### Stage 3 — Multi-Attribute Fuzzy PSI (`PSIService.run_psi(enable_fuzzy=True)`)

`psi_service.py :: run_psi(bank_a_id, bank_b_id, entity_type, enable_fuzzy=True, fuzzy_threshold=3)` executes a threshold-based multi-attribute matching protocol:

1. **Attribute Set**: 5 key PII attributes are evaluated per entity pair: `phone`, `email`, `device_id`, `birthdate`, `surname`.
2. **Independent DH-PSI per Attribute**: Standard Diffie-Hellman commutative exponentiation is executed independently over each attribute's `PrivacyPreservingIdentifier` hash:
   $$Z_a^{(\text{attr})} = \left( H(\text{attr}_a) \right)^{k_b \cdot k_a} \pmod p$$
3. **k-of-n Threshold Gate**: A cross-bank pair is declared a match if:
   $$\left| \text{matched\_attrs} \right| \ge k \quad (\text{default: } k = 3 \text{ of } n = 5)$$
4. **Similarity Score**: The output match record includes a continuous overlap score $= |\text{matched\_attrs}| / n$.

#### Stage 4 — Central LSH Registry (`EntityResolutionService.resolve_fuzzy_entities()`)

`entity_resolution.py :: resolve_fuzzy_entities(query_name, entity_type, threshold=0.70)` provides a direct name-to-entity fuzzy lookup:
- Standardizes and computes the MinHash signature of the query string.
- Iterates all stored entities, reads their `minhash_signature` attribute, and computes Jaccard similarity.
- Returns all entities above the configurable similarity threshold, sorted by descending similarity.
- Exposed to the frontend via `POST /api/v1/entities/fuzzy-resolve`.

#### Frontend Integration (`PsiPage.tsx`)

The `PsiPage` React component provides an interactive three-panel UI:
- **PSI Protocol Control Center**: Configures bank pair, entity type, Intel SGX TEE toggle, fuzzy enable/disable, and threshold slider (k = 1–5).
- **MinHash Spelling Playground**: Local JavaScript implementation of `standardize_input()` and `compute_minhash_signature()` that shows real-time 16-dimensional signature comparison and Jaccard score for any two name inputs without making API calls.
- **Central LSH Registry Query Panel**: Calls `/api/v1/entities/fuzzy-resolve` and displays matched entities with similarity scores, bank, risk level, standardized form, and privacy hash.

#### Test Coverage

`backend/tests/unit/test_fuzzy_psi.py` covers:
- `test_standardization_pipeline`: Validates Turkish/accented names, E.164 phone normalization, and email stripping.
- `test_minhash_lsh`: Asserts identical signatures for identical inputs (sim = 1.0), high similarity for near-typo variants (sim > 0.3), and low similarity for completely different strings (sim < 0.2).
- `test_fuzzy_psi_protocol`: End-to-end test with 3 entities and 2 threshold levels (k=3 matches 1 pair; k=2 matches 2 pairs).



### 2. Graph Analytics & Risk Propagation

Once matches are resolved, a multi-bank transaction graph is constructed. The engine executes three structural graph algorithms:

* **PageRank-Like Risk Propagation**: Starting with known high-risk/critical alerts, risk scores are propagated to neighboring nodes using a decay factor ($\gamma = 0.85$) and weight adjustments based on relationship type (e.g. `SHARES_DEVICE` has higher weight than `SHARES_IP`).
* **Community Analytics**: Connected components are grouped, and community-level statistics (size, average risk, and fraud density) are computed to isolate potential fraud rings.
* **Temporal Velocity Anomalies**: Edges are grouped in sliding time windows (e.g., 5 minutes) to detect high-velocity relationship creation bursts that signal structuring or automated laundering networks.

### 2.5 Dedicated Distributed Graph Database Integration (Neo4j / Memgraph)

To handle massive scales of customer relationships, transactions, and alert linkages at sub-second latency, the Graph Engine supports a dedicated, distributed graph database backend (Neo4j or Memgraph) via the Bolt protocol.

* **Cypher Queries**: Replaces CPU-bound custom Python traversal loops (BFS/DFS) with highly optimized Cypher queries executed directly in the database.
  - *Neighbor Search query*:
    ```cypher
    MATCH (s:Entity {id: $entity_id})-[r]-(n:Entity)
    WHERE ($relationship_types IS NULL OR r.relationship_type IN $relationship_types)
    RETURN DISTINCT n
    ```
  - *Subgraph Extraction query*:
    ```cypher
    MATCH (s:Entity {id: $center_id})
    OPTIONAL MATCH p = (s)-[*1..$radius]-(n:Entity)
    RETURN s, collect(p) as paths
    ```
* **Real-time GNN Serving**: Enables compatibility with real-time Graph Neural Network inference runtimes (e.g. Memgraph GNN modules / DGL) to update node embeddings dynamically as new transaction edges are written.
* **Dual-Storage & Fallback**: Configured via `graph_db_type` in settings (supporting `"redis"`, `"neo4j"`, `"memgraph"`). If the graph database is not reachable or not installed, the engine gracefully falls back to the Redis / in-memory adjacency list to maintain complete backward compatibility in development.

### 3. Federated Graph Embedding (FedGNN)


To move beyond heuristic relationship weights, Phase 5 introduces a **Federated GraphSAGE** (Sample and Aggregate) pipeline to learn structural graph embeddings collaboratively:

1. **Local Graph Representation**: Each bank constructs a graph mapping its entities to a 12-dimensional numerical feature representation (entity types, risk levels, alert logs, local degrees, and activity recency).
2. **GraphSAGE Model**: A 2-layer GraphSAGE architecture performs message-passing:
   $$\mathbf{h}_{\mathcal{N}(v)}^{(k)} = \text{AGGREGATE}\left(\{\mathbf{h}_u^{(k-1)}, \forall u \in \mathcal{N}(v)\}\right)$$
   $$\mathbf{h}_v^{(k)} = \sigma\left(\mathbf{W}^{(k)} \cdot \left[\mathbf{h}_v^{(k-1)} \,\|\, \mathbf{h}_{\mathcal{N}(v)}^{(k)}\right]\right)$$
3. **Federated Aggregation**: Only GNN parameters ($\mathbf{W}^{(k)}$ projection weights) are sent to the coordinator. The coordinator aggregates GNN parameters using Krum or FedAvg, then redistributes the global GNN.
4. **Downstream Analytics**:
   - **Embedding-Enhanced Propagation**: Connected node risk transfer weights are calculated dynamically using cosine similarity of GNN embeddings rather than hardcoded heuristics.
   - **Unconnected Clustering**: Nodes are clustered across banks by embedding similarity, isolating coordinated syndicate networks that share a modus operandi without having a direct edge connection in the graph.

---

## Decentralized Infrastructure & Network Isolation (Production Design)

To move away from monolithic or shared environments, the production-grade simulator models a multi-VPC decentralized cloud architecture using distinct networks and database containers.

### 1. Security Boundaries & Network-Level VPC Simulation
The system is divided into four private, isolated security zones and one shared federation channel:
- **Bank Client Private Zones (`net-bank-a`, `net-bank-b`, `net-bank-c`)**: Contains the respective Bank Client microservice and its **isolated database container** (e.g. `postgres-bank-a`). No database port is exposed to other networks or the host, preventing cross-bank data leakage.
- **Coordinator Private Zone (`net-coordinator`)**: Hosts the central control plane, including the Gateway, Federated Learning Coordinator, Identity & Graph Service, Fraud & Alert Engine, Celery Workers, Flower, Redis Event Broker, Jaeger, Prometheus, Grafana, and the coordinator database.
- **Federation Network Channel (`net-federation`)**: A dedicated network bridge restricted to cross-zone communications. Only the `fl-coordinator` and the bank clients (`bank-a`, `bank-b`, `bank-c`) have interfaces on this network.

```mermaid
graph TD
    subgraph VPC Bank A
        postgres-a[(Postgres Bank A)]
        bank-a[Bank Client A Service]
        bank-a --- postgres-a
    end

    subgraph VPC Bank B
        postgres-b[(Postgres Bank B)]
        bank-b[Bank Client B Service]
        bank-b --- postgres-b
    end

    subgraph VPC Bank C
        postgres-c[(Postgres Bank C)]
        bank-c[Bank Client C Service]
        bank-c --- postgres-c
    end

    subgraph VPC Coordinator Control Plane
        fl-coord[FL Coordinator]
        postgres-coord[(Coordinator Postgres)]
        gateway[API Gateway]
        redis[Redis Event Bus]
        fl-coord --- postgres-coord
    end

    %% Federation Links
    fl-coord ===|net-federation| bank-a
    fl-coord ===|net-federation| bank-b
    fl-coord ===|net-federation| bank-c
```

### 2. Mutual Auth & Cryptographic Payload Signing
To protect the REST communication channel between the `fl-coordinator` and the `bank-client` nodes on `net-federation`, the API implements **end-to-end payload signing**:
1. **Outbound Request Signing**: The coordinator computes an HMAC-SHA256 signature using the shared `PAYLOAD_SIGNING_SECRET`, the current Unix timestamp, and the request body:
   $$\text{Signature} = \text{HMAC-SHA256}(\text{Secret}, \text{Timestamp} \mathbin{\Vert} \text{Payload Bytes})$$
2. **Transmission**: The request is sent with the custom headers `X-Payload-Signature` and `X-Payload-Timestamp`.
3. **Inbound Validation**: The bank client validates that:
   - The timestamp header is present and is within a $\pm 300\text{s}$ tolerance window (mitigating replay attacks).
   - The HMAC computed locally over the received raw request body matches the signature header.
4. **Rejection**: If signature verification fails, the request is rejected with a `401 Unauthorized` response.

---

## Real-Bank Connector Integrations (Phase 6 Production Design)

To support seamless transitions from simulation to production banking architectures, the platform implements standardized, production-ready interfaces for core banking systems (CBS), standard messaging formats, open banking APIs, and message queues.

```mermaid
graph TD
    subgraph Core Banking Integration
        REST[RESTBankConnector] -->|OAuth2 / mTLS| CBS[Core Banking System]
        MQ[RabbitMQBankConnector] -->|AMQP / Pika| Queue[RabbitMQ Broker]
    end

    subgraph Standard Messaging
        Parser[FinancialMessageParser]
        Parser -->|Ingests| ISO[ISO 20022 XML pacs.008]
        Parser -->|Ingests| SWIFT[SWIFT MT103]
        Parser -->|Ingests| SEPA[SEPA Credit Transfer XML]
    end

    subgraph Open Banking PSD2 XS2A
        Router[PSD2 Router] -->|Bearer JWT Auth| AISP[Third-Party AISP Client]
        Router -->|Checks Consent| Consents[(Consent Store)]
    end
```

### 1. Production-Grade CBS Adapters
* **mTLS Integration**: The `RESTBankConnector` checks for configured client certificate files at runtime. If present, it establishes secure HTTPS connections using mutual TLS certificate verification.
* **OAuth2 Authentication**: For systems requiring token-based access, the adapter dynamically requests OAuth2 Client Credentials tokens from the configured authorization server (`oauth_token_url`), caches them locally, and attaches them as Bearer tokens to outbound requests.

### 2. Financial Message Parsers
The `FinancialMessageParser` normalizes real-time and bulk financial messages into transaction entities:
* **ISO 20022 (pacs.008)**: Parses structured XML schemas to extract end-to-end IDs, settlement amounts, currencies, debtor (sender) and creditor (receiver) names, IBANs, and BICs.
* **SWIFT MT103**: Parses flat legacy SWIFT messages by scanning block 4 tags (e.g., `:20:` for reference, `:32A:` for value date/amount, `:50K:`/`:59:` for customer info).
* **SEPA credit transfers**: Standardizes incoming instant and credit transfer pain.001 or pacs.008 messages into the platform's schema.

### 3. Open Banking PSD2 API
The platform exposes standardized endpoints compliant with the PSD2 XS2A (Access to Account) mandate:
* **Consent Management (`/api/v1/psd2/consents`)**: Allows third-party providers (AISPs) to register account access scopes and expiration dates.
* **Account Access (`/api/v1/psd2/accounts`)**: Retrieves details of accounts matching active consents.
* **Transaction Ingestion (`/api/v1/psd2/accounts/{account_id}/transactions`)**: Exposes historical transactions under active AISP consents.
* **Bearer JWT Security**: Endpoints require JWT validation signed with a secure secret, verifying standard claims (`sub`, `scope`, and expiration timestamp).

### 4. Enterprise Message Queues (RabbitMQ)
* **Concrete RabbitMQ Connector**: Implements `BankConnectorInterface` using the `pika` library. It publishes tasks to durable queues (`fl.queue.{bank_id}.train`, etc.) and consumes responses on dynamic, exclusive callback queues using matching correlation IDs.
* **Resilient Failover**: If the RabbitMQ broker is unreachable, the connector falls back to local in-memory nodes (`MockBankConnector`), preventing orchestration failure during local testing.

