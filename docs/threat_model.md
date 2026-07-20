# Threat Model

> Security and privacy analysis of the Collaborative Fraud Intelligence Simulator.

---

## 1. Trust Model

### Actors

| Actor | Trust Level | Description |
|-------|-------------|-------------|
| **Central Server** | Honest-but-curious | Follows the protocol but may attempt to infer private data from observed updates |
| **Bank Clients** | Semi-honest | Execute local training correctly but may be compromised |
| **External Adversary** | Untrusted | Network attacker attempting to intercept or modify communications |

### Assumptions

1. Banks trust the aggregation server to not collude with other banks
2. Banks correctly implement local training (no model poisoning)
3. The aggregation protocol is followed faithfully
4. Network channels are encrypted (TLS in production)

---

## 2. Privacy Threats

### 2.1 Model Update Inference

**Threat**: An adversary observing raw model updates could infer properties of a bank's training data.

**Attack vector**: Gradient inversion attacks can reconstruct training examples from shared gradients, especially with small batch sizes or high-dimensional models.

**Mitigations in this system**:

| Mitigation | How It Works | Effectiveness |
|------------|-------------|---------------|
| **Differential Privacy** | Gaussian noise calibrated to (ε, δ) added to updates | Provable privacy guarantee. Lower ε = stronger privacy. |
| **Gradient Clipping** | L2 norm of update bounded by `max_grad_norm` | Limits the influence of any single data point |
| **Secure Aggregation** | Server sees only the sum, not individual updates | Prevents server from isolating any single bank's contribution |
| **Batch Training** | Updates are averaged over mini-batches (default 64) | Individual samples are diluted |

### 2.2 Membership Inference

**Threat**: Determine whether a specific transaction was in a bank's training set.

**Mitigation**: Differential privacy with (ε, δ)-guarantees provides formal bounds on membership inference advantage. With ε=1.0, the adversary's advantage is bounded by e^ε ≈ 2.72x over random guessing.
*   **Active MIA Audit**: The system runs a post-training **Membership Inference Attack (MIA)** audit using the `PrivacyAuditService`. It compares training and test loss distributions, setting a dynamic classification threshold to verify that the attack success rate (ASR) does not exceed acceptable security boundaries (e.g. ASR ≈ 0.5 for random guessing).

### 2.3 Model Memorization

**Threat**: The trained model memorizes and leaks specific transactions.

**Mitigation**: The MLP architecture with dropout (0.3, 0.2) and batch normalization reduces overfitting. DP noise further prevents memorization of individual examples.

### 2.4 GNN Link and Attribute Reconstruction (FedGNN)

**Threat**: An adversary or semi-honest server attempts to reconstruct the local bank's transaction graph topology (e.g., who transacts with whom) or node attributes from shared GraphSAGE model updates.

**Mitigations in this system**:
- **Gradient/Weight Clipping & DP**: Like the MLP classifier, GNN weight updates are clipped and noised (Gaussian mechanism) before sharing. This bounds the impact of any single edge or node connection on the aggregated model parameters.
- **Aggregator Mean-Pooling**: In GraphSAGE, neighbors are aggregated using permutation-invariant mean pooling. An observer of weights cannot easily reconstruct specific neighborhood graph connections since local adjacency structures are compressed into aggregated local features before gradient computation.
- **Edge Dropout / Mini-batch Sampling**: Neighborhood sampling during GraphSAGE forward passes naturally acts as an edge-level dropout defense, preventing the model from over-fitting to specific node-link structures.
- **Active LRA Audit**: The system implements an active **Link Reconstruction Attack (LRA)** vulnerability audit inside `PrivacyAuditService`. By computing the cosine similarity of node representation updates between linked and unlinked pairs, it computes the area under the ROC curve (AUC). A low AUC (close to 0.5) mathematically proves that an adversary cannot reconstruct the topology.

---

## 3. Integrity Threats

### 3.1 Model Poisoning

**Threat**: A compromised bank sends malicious model updates to degrade the global model or introduce a backdoor.

**Status in simulator**: Fully mitigated and configurable via robust aggregation defenses.

**Simulator mitigations**:
- **Byzantine Defenses (Krum)**: The simulator implements the Krum aggregation algorithm (Blanchard et al., 2017), which computes pairwise distances between client model updates and selects the representative update that is closest to its neighboring models. This successfully detects and discards poisoned updates from malicious/outlier banks.
- **Coordinate-wise Median**: Evaluates the median value independently for each model parameter across all participating bank updates. This filters out coordinate-wise outlier gradient injections.
- **Adversarial Simulation Toggles**: The UI allows simulating a poisoning attacker (e.g. Bank C scaling its weights maliciously) to test the vulnerability of standard FedAvg versus Krum or Median aggregation.

### 3.2 Data Poisoning

**Threat**: A bank contaminates its local training data to influence the global model.

**Status**: Out of scope for this simulator (data is synthetically generated and controlled).

### 3.3 Free-Riding

**Threat**: A bank sends random or minimal updates while benefiting from the global model.

**Status**: Not mitigated. Could be detected via update norm monitoring.

---

## 4. Availability Threats

### 4.1 Client Dropout

**Threat**: Banks go offline during training, disrupting the protocol.

**Mitigations**:
- Minimum quorum enforcement (default: 2/3 banks required)
- Graceful skip of rounds with insufficient participants
- Reconnection mechanism for previously dropped clients

### 4.2 Denial of Service

**Threat**: Overwhelming the aggregation server.

**Status**: Out of scope for single-machine simulator. Production would use rate limiting and authentication.

---

## 5. Privacy Budget Analysis

With default settings (ε=1.0, δ=1e-5) over 10 rounds:

| Parameter | Value |
|-----------|-------|
| Per-round ε | 1.0 |
| δ | 1e-5 |
| Total ε (10 rounds, basic composition) | 10.0 |
| Max gradient norm | 1.0 |
| Noise multiplier (σ/C) | ~5.3 |
| **Strict DP Budget Limit** | 8.0 (Configurable) |

**Note**: Basic sequential composition is used. Advanced composition (Rényi DP, moments accountant) would yield tighter bounds. In production, use the `opacus` library for rigorous privacy accounting.
*   **Strict DP Budget Monitor**: The simulator implements an automated privacy budget monitor (`PrivacyBudget.spend`). If the cumulative spent privacy budget exceeds the configured safety threshold (default `dp_epsilon_limit = 8.0`), it immediately throws a `PrivacyBudgetExceededError` and halts the federated simulation to prevent further privacy loss.

---

## 6. Gap Analysis — Simulator vs Production

| Security Property | Simulator | Production Target |
|---|---|---|
| Transport encryption | **Mutual TLS 1.3 (mTLS) with SAN & CRL Checks** | TLS 1.3 mutual auth |
| Client authentication | **OIDC / OAuth2 JWT Bearer Tokens + ABAC** | mTLS + OIDC / OAuth2 + ABAC |
| Secure aggregation | Simulated pairwise masks | MPC (SPDZ, SecureNN) or **Secure Enclaves (Intel SGX / AMD SEV)** |
| Private Set Intersection (PSI) | Simulated DH-PSI / **Secure TEE Enclave Matching** | **Hardware Enclave (Intel SGX)** or Multi-party Computation (MPC) |
| DP accounting & Budgeting | Basic composition + **Strict Budget Limit Gating** | Rényi DP (moments accountant) + Budget limits |
| Byzantine resilience | **Krum / Median Implemented** | Krum / Trimmed Mean |
| Audit logging & Vulnerability Audits | **SHA-256 Cryptographic Hash Chain Ledger ($H_i = \text{SHA256}(L_i \Vert H_{i-1})$)** | Tamper-evident audit trail + Real-time vulnerability scanning |
| Key management & Secrets | **HashiCorp Vault KV v2 Secret Engine Client** | HSM-backed key infrastructure / HashiCorp Vault |

This gap analysis is intentional — the simulator demonstrates the concepts and simulates hardware constraints. Production deployment requires hardening each layer.

---

## 7. STRIDE Threat Classification

The system architecture and interfaces are mapped against the **STRIDE** security threat taxonomy (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) to catalog security coverage:

| Threat Category | Specific Threat Description | Affected Components | Active Mitigations | Production Gap / Residual Risk |
|:---|:---|:---|:---|:---|
| **Spoofing** | A compromised or malicious node masquerades as a verified participating bank to send false parameters or steal global weights. | FL Aggregation Coordinator, WebSockets | **mTLS 1.3 X.509 PKI** with SAN verification (`mtls_manager.py`), OIDC JWT validation | Certificate revocation propagation latency. |
| **Tampering** | A participant alters local parameters to degrade model performance (Model Poisoning) or inject backdoors. | Pytorch Training, FedAvg Engine | Byzantine-Robust aggregation (Krum, Coordinate-wise Median), **SHA-256 Cryptographic Audit Chain** | Attack scale threshold limits. If $>50\%$ of nodes are compromised, median fails. |
| **Repudiation** | An attacker performs malicious actions (e.g., model poisoning) and denies execution due to lack of non-repudiation logs. | Microservices Gateway | **Tamper-Proof SHA-256 Audit Chain ($H_i = \text{SHA256}(L_i \Vert H_{i-1})$)** with 1-click retrospective verification | Offline ledger backup frequency. |
| **Information Disclosure** | Passive intercept of model weights allows gradient inversion, reconstructing raw transaction features or identity fields. | Network Gateway, Aggregation Engine | Differential Privacy (L2 clipping + noise), Secure Aggregation masking, **HashiCorp Vault Secret Isolation** | Basic composition limits budget tracking. Requires advanced accounting. |
| **Denial of Service** | A client drops offline or sends malformed weights, stalling coordinator aggregation routines. | flower_engine, Celery Workers | Quorum checks ($\ge$ Min Clients), timeout intervals, fallback state | Distributed denial of service on gateway endpoints. |
| **Elevation of Privilege** | An unauthorized client gains access to case management records or starts scenarios via gateway. | gateway API router | **Dynamic ABAC Engine** (multi-tenant bank isolation, shift hour restrictions, approval tier limits, clearance levels), OIDC JWT claims | Policy misconfiguration risks. |


---

## 8. OWASP ASVS (Application Security Verification Standard) v4.0 Mapping

The security configuration maps against the following **ASVS Level 2** controls, identifying compliance status:

*   **V1 Architecture, Design and Threat Modeling:**
    *   *1.1.1 (Secure Software Development Lifecycle):* **Secure.** Simulator implements automated unit verification checks (`pytest`) and code formatting quality gates (`ruff`).
    *   *1.1.2 (Threat Modeling):* **Secure.** Detailed trust boundaries and data flow assets defined within this threat model document.
*   **V2 Authentication Verification Requirements:**
    *   *2.10.1 (API Key Management):* **Partial.** API Gateway supports salted token checks but relies on environment configurations rather than dynamic vault storage.
*   **V3 Session Management Verification Requirements:**
    *   *3.4.1 (State Isolation):* **Secure.** Replicated stateless tasks and Redis session layers prevent cross-tenant memory leakage.
*   **V5 Input Validation, Security Gate, and Parameter Handling:**
    *   *5.1.1 (Sanitization):* **Secure.** Deep FastAPI Pydantic type constraints enforce strict schemas on all simulation configs, alerts, and cases endpoints.
*   **V8 Data Protection Verification Requirements:**
    *   *8.1.1 (Sensitive Data Storage):* **Secure.** Bank data remains entirely localized on memory frames during iterations. No transaction databases are shared.
*   **V9 Communication Security Verification Requirements:**
    *   *9.1.1 (Transport Security):* **Gap.** Simulator operates on HTTP/WS localhost channels. Production target requires TLS 1.3 mutual auth.
*   **V11 Business Logic Verification Requirements:**
    *   *11.1.1 (Canary Gate Promotion):* **Secure.** Newly trained aggregated models are evaluated on a holdout validation set and compared with the active model. Models are only promoted if they pass the gate.

---

## 9. MITRE ATLAS (Adversarial ML) Taxonomy Mapping

Adversarial ML risks are audited against the **MITRE ATLAS** (Adversarial Threat Landscape for Artificial-Intelligence Systems) matrix:

*   **AML.TA0001 — Reconnaissance (Active/Passive):**
    *   *Technique:* AML.T0002 (Identify Sensitive Data). An attacker attempts to discover transaction fields by intercepting weights.
    *   *Mitigation:* Salted one-way HMAC entity masking prevents reverse lookup of raw PII elements.
*   **AML.TA0002 — Initial Access:**
    *   *Technique:* AML.T0006 (Compromise Client Node). Adversary compromises Bank C's local trainer process.
    *   *Mitigation:* Aggregation coordinator operates outside the trust boundaries of individual clients, utilizing sandboxed PyTorch execution threads.
*   **AML.TA0003 — Execution:**
    *   *Technique:* AML.T0009 (User Execution of Malicious Model). Promoting a compromised global model to downstream banks.
    *   *Mitigation:* **Canary Evaluation** blocks promotion of poisoned weight updates if validation performance drops.
*   **AML.TA0005 — Defense Evasion:**
    *   *Technique:* AML.T0015 (Poisoning Attack). Scaling adversarial gradient weights to bypass FedAvg averages.
    *   *Mitigation:* **Krum** Byzantine-robust aggregation isolates the outlier updates, neutralizing poisoning attempts.
*   **AML.TA0009 — Exfiltration:**
    *   *Technique:* AML.T0024 (Model Inversion). Reconstructing training distribution records.
    *   *Mitigation:* **Differential Privacy** adds calibrated Gaussian noise, mathematically bounding reconstruction success probability.

---

## 10. Data Integrity & Streaming Security

### 10.1 Data Poisoning via Corrupt Input

**Threat**: Malformed or statistically anomalous transaction batches (null values, invalid currency codes, extreme amounts) silently corrupt GNN embeddings or cause training runtime crashes.

**Mitigations**:
*   **Pandera Schema Validation**: Enforces strict dataframe schemas at the streaming consumer boundary. Validates ISO 2-letter country codes, positive transaction amounts, valid categorical values (device types, merchant categories), and numeric range constraints.
*   **Great Expectations Data Contract Gating**: Runs automated statistical stability checks (null ratio assertions, mean transaction amount confidence intervals, categorical distribution validation) on each bank's data prior to local model training. Failing batches are quarantined and trigger system alerts.

### 10.2 Event Stream Tampering

**Threat**: In-transit event messages (alerts, training updates) could be reordered, duplicated, or dropped, causing inconsistent system state.

**Mitigations**:
*   **Apache Kafka/Redpanda Backbone**: When enabled, replaces Redis Pub/Sub with a fault-tolerant, append-only log. Events are partitioned by bank ID, ordered by offset, and durably persisted. Consumer groups provide exactly-once semantics.
*   **Event Metadata Injection**: Each published event is tagged with topic, partition, offset, broker address, and millisecond timestamp for full audit traceability.

### 10.3 Database Consistency Under High Write Load

**Threat**: Concurrent high-throughput transaction writes cause serialization conflicts, phantom reads, or silent data loss under standard isolation levels.

**Mitigations**:
*   **CockroachDB Serializable Isolation**: When configured with `database_type=cockroachdb`, the platform operates under strict SERIALIZABLE isolation, preventing phantom reads and write skew anomalies.
*   **Application-Level Transaction Retries**: The `run_cockroach_transaction` utility automatically retries on SQLSTATE 40001 (serialization conflict) with configurable max retries, ensuring transactional consistency without silent failures.

---

## 11. Enterprise Federated Coordinator Threat Surface (Item 18)

The `CoordinatorService` introduces a dynamic network control plane with its own threat surface:

### 11.1 Rogue Node Registration (Spoofing)

**Threat**: An unauthorized actor sends a `POST /handshake` request impersonating a legitimate bank node to inject malicious training parameters or access the active client list.

**Mitigations**:
* **Runtime Compatibility Gate**: The handshake validates `pytorch_version ≥ 2.x` and `python_version ≥ 3.10`. Nodes failing version checks are rejected before registration.
* **Gateway HMAC Signing**: All requests transit the API Gateway, which enforces `X-Payload-Signature` HMAC-SHA256 header validation with a 5-minute replay prevention window.
* **Future Enhancement**: Token-based bank identity assertion (OAuth2 Client Credentials per bank) should be layered on the handshake for production deployments.

### 11.2 Heartbeat Flooding (Denial of Service)

**Threat**: An adversary floods `/heartbeat` endpoints to keep a malicious node marked ONLINE indefinitely, or to exhaust API Gateway rate limits.

**Mitigations**:
* **Fixed-Window Rate Limiter**: The API Gateway applies per-client rate limits to all coordinator endpoints.
* **Bank ID Allowlist**: Only bank IDs present in the active registry can submit heartbeats; unregistered IDs return HTTP 404.

### 11.3 Parameter Manipulation (Tampering)

**Threat**: A compromised bank node queries `/negotiate` with falsified hardware specifications (e.g., claiming 64GB CUDA) to receive full training parameters while running on an under-provisioned CPU node, causing gradient staleness and aggregation divergence.

**Mitigations**:
* **Server-Side Capability Store**: Hardware capability is stored server-side at registration time. The negotiate endpoint reads from the registry — the client cannot alter its stored hardware profile via the negotiate query.
* **Parameter Validation**: Batch size and epoch values are clamped server-side regardless of reported hardware.

### 11.4 Client Dropout & Quorum Attack (Elevation of Privilege)

**Threat**: A coordinated DoS attack sends no heartbeats from legitimate nodes, causing them to be marked OFFLINE. The attacker's compromised node becomes the sole ONLINE participant and dominates aggregation.

**Mitigations**:
* **Minimum Quorum Enforcement**: The FL engine's `min_clients_per_round` setting aborts rounds when active ONLINE clients fall below threshold, preventing single-node dominance.
* **Byzantine-Robust Aggregation**: Even if only attacker nodes participate, Krum and Coordinate-wise Median reject outlier updates.

| STRIDE Category | Coordinator Threat | Mitigation |
|:---|:---|:---|
| **Spoofing** | Rogue bank registration via `/handshake` | HMAC gateway signing, runtime version gate |
| **Tampering** | False hardware specs to `/negotiate` | Server-side capability registry (read-only from client) |
| **Repudiation** | Deny sending malicious heartbeats | Heartbeat timestamps logged to registry with `time.time()` |
| **Information Disclosure** | Enumerate active banks via `/clients` list | Gateway RBAC restricts endpoint to authorized roles |
| **Denial of Service** | Heartbeat flood to exhaust rate limits | Fixed-window rate limiter at gateway layer |
| **Elevation of Privilege** | Dropout attack leaves one malicious node | Min-quorum enforcement + Krum/Median aggregation |

---

## 12. Advanced Privacy Defense & Attack Benchmarking Threat Surface (Item 19)

The introduction of the `PrivacyAuditService` and new robust aggregation methods (Bulyan, Trimmed Mean) adds defense-in-depth but also introduces a new threat surface related to malicious evaluation inputs and budget exhaustion.

### 12.1 Colluding Byzantine Byzantine Attackers (Spoofing & Tampering)

**Threat**: A group of coordinated malicious banks submit colluding, poisoned model updates that fool single-median or simple Krum heuristics by clustering around a false point.
**Mitigations**:
* **Bulyan Aggregation**: The simulator implements **Bulyan** (El Mhamdi et al. 2018), which applies a nested selection process (Krum followed by Trimmed Mean). This successfully filters out colluding attackers when up to $f$ nodes are malicious (where $c \ge 4f + 3$).
* **Coordinate-wise Trimmed Mean**: Discards the $f$ largest and $f$ smallest values along each coordinate, neutralizing gradient boosting or sign-flipping attacks.

### 12.2 Privacy Budget Exhaustion Attack (Information Disclosure)

**Threat**: A malicious participant initiates a high volume of federated learning simulations to sequentially extract small amounts of information from the model updates, accumulating total privacy leakage ($\epsilon$) beyond safe bounds.
**Mitigations**:
* **Enterprise Privacy Budget Log**: The `PrivacyService` tracks cumulative $\epsilon$ spend across all simulations.
* **Hard Budget Limit & Fail-Safe**: If any simulation's cumulative $\epsilon$ exceeds `epsilon_limit` (default 8.0), the engine triggers a `PrivacyBudgetExceededError` and halts aggregation, preventing further information leakage.
* **Exhaustion Audits**: The dashboard alerts administrators dynamically if any simulation enters the `EXHAUSTED` state.

### 12.3 Attack Audit Poisoning (Tampering & Denial of Service)

**Threat**: An adversary submits malformed, infinite, or NaN loss lists/gradient vectors to `/audit/mia` or `/audit/dlg` to cause division-by-zero or memory exhaustion on the server.
**Mitigations**:
* **Schema Validation & Fallbacks**: The inputs are validated through Pydantic. If empty lists or single elements are provided, the audit service falls back to safe defaults (e.g., ASR = 0.5, risk = safe) instead of crashing.
* **NaN Handling**: Cosine similarity and Pearson correlation computations filter out NaN values and enforce bounds.

| STRIDE Category | Privacy/Defense Threat | Mitigation |
|:---|:---|:---|
| **Spoofing** | Colluding nodes inject false model updates | Bulyan double-filtering strategy |
| **Tampering** | Malformed gradient norms sent to DLG audit | Standard deviation bounds and NaN/empty list safeguards |
| **Repudiation** | Deny initiating budget-exhausting simulations | Persistent budget logs tracked by simulation ID |
| **Information Disclosure** | Scraping model secrets via repeated aggregation | Hard global privacy budget limits per simulation |
| **Denial of Service** | Submitting infinite parameters to attack audits | Fixed-window rate limiter + Pydantic validation |
| **Elevation of Privilege** | Bypassing DP noise checks | Global accountant checks at the coordinator boundary |

