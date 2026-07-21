# Collaborative AML Intelligence Platform

This document describes the privacy-preserving cross-bank Anti-Money Laundering (AML) features added in Phase 2 of the Collaborative Fraud Intelligence Simulator.

## Overview

Traditional AML tools operate in isolation, looking only at transactions within a single bank. This leaves blind spots for cross-institution activity, such as:
1. **Multi-bank fraud rings** where malicious actors share devices or bank accounts across different institutions.
2. **Layering patterns** where funds are split into smaller transactions and routed through multiple banks to stay below reporting thresholds.
3. **Distributed card testing** where stolen cards are verified via small purchases across multiple banks before executing a large purchase.

The Collaborative AML Intelligence Platform enables banks to resolve entities and share intelligence to address these blind spots without exposing private customer transaction histories.

---

## Core AML Features

### 1. Collaborative Alert Intelligence
When a bank's local model flags a transaction, it generates a local alert. The bank can optionally publish a stripped-down, privacy-preserving indicator of this alert to the shared layer.
* **Hashed Identifiers**: The shared indicator contains only a deterministic hash of the transaction or customer, not raw PII.
* **Risk Indicator**: A normalized value representing the bank's assessment confidence.
* **Reason Codes**: Standard codes (e.g. `VEL-001` for velocity, `GEO-RISK` for high-risk country) that help other banks assess relevance.

### 2. Privacy-Preserving Entity Resolution
To correlate activity across banks without disclosing PII, the platform utilizes **deterministic HMAC-SHA256 hashing**.
* Each bank hashes sensitive identifiers (e.g., customer emails, phone numbers, or account IDs) using a shared HMAC key.
* The resulting hashes are compared at the shared layer. If `bank_a` and `bank_b` both see the hash `e3b0c442...`, they know they are dealing with the same real-world entity without ever knowing who that customer is.

### 3. Entity Relationship Graph
Resolved entities and their connections are mapped in an in-memory relationship graph:
* **Nodes**: Represent privacy-preserving entities (Customers, Devices, Merchants, IP Addresses).
* **Edges**: Represent relationships (owns account, transacted with merchant, used device, shared IP address).
* **Interactive Visualization**: Serialized to React Flow for visual representation, highlighting high-risk clusters that indicate organized crime.

### 4. 9-Signal Risk Engine
A composite risk scoring pipeline combines multiple independent signals to produce a unified score between `0` and `1000`:
1. **ML Model Prediction**: Federated model classification score.
2. **Velocity Rules**: Rate of transactions per hour.
3. **Merchant Reputation**: Historical fraud rates at the target merchant.
4. **Geographical Risk**: Origin of transaction (e.g., known high-risk country codes).
5. **Device Anomaly**: High-risk device categories or channels (e.g., telephone banking).
6. **Customer History**: Historical customer score and account age.
7. **Previous Alerts**: Prior alerts generated for this entity.
8. **Chargeback History**: Historical chargeback rates.
9. **Behavior Anomaly**: Deviation from the customer's typical transaction baseline.

---

## Fraud Scenarios Simulator

The platform includes a real-time scenario simulator to showcase how collaborative intelligence improves detection over single-bank observation:

1. **Cross-Institution Fraud Ring**:
   * *Behavior*: 4 actors share devices and IP addresses to execute transactions across 3 banks.
   * *Outcome*: Individual banks see separate events with a medium confidence (~62%). Collaborative resolution connects the nodes, triggering a critical alert (~91% confidence).
2. **Account Takeover (ATO)**:
   * *Behavior*: Attacker registers a new device, changes contact details, and executes rapid withdrawals.
   * *Outcome*: Cross-bank intelligence flags the synchronized target profile and escalates the risk rating immediately.
3. **Layered Money Laundering**:
   * *Behavior*: Large deposit at bank A is split into sub-threshold payments to banks B & C before being consolidated.
   * *Outcome*: Individually, the transactions look like small, normal wires. The shared intelligence layer tracks the split flow and highlights the layering pattern.
4. **Card Testing**:
   * *Behavior*: Cards are tested with sub-$5 transactions at different merchants/banks.
   * *Outcome*: Individual banks ignore the minor transactions. Graph correlation links the test charges to reveal the card testing ring before large-scale card draining occurs.

---

## 🧬 Feature Store Integration (Feast / Hopsworks)

To handle production scale and meet strict SLA latency bounds (<50ms), the platform integrates a dual offline-online Feature Store (simulating Feast / Hopsworks):

### 1. Online Feature Store (Redis-backed)
- Serves live features to the `RiskScoringEngine` and MLP inference pipeline in real time.
- Uses a unified entity mapping (`customer_id`, `merchant_id`) to pull aggregated vectors under strict latency bounds (<5ms execution).

### 2. Offline Feature Store (Snowflake / BigQuery)
- Provides point-in-time joins (`get_historical_features`) over historical logs.
- Guarantees data leakage prevention by ensuring features represent the state of entities exactly as they existed at the transaction timestamp.

### 3. Dynamic Streaming Pipelines (Apache Flink / Spark Streaming)
- Transactions ingested into the API stream directly update sliding window features:
  - `rolling_velocity_1h`: Counts customer transactions in the last hour.
  - `avg_amount_24h`: Running average amount of customer transactions in the last 24 hours.
- Updates are pushed instantly to the Online Store to protect downstream scoring from high-velocity rings.

---

## 🏦 Real-Bank Connector Integrations (Phase 2 Task 6)

To interface with live production financial systems, the platform provides three concrete connector implementations and parsing services:

### 1. Core Banking System (CBS) Adapters
- **REST Connector (`RESTBankConnector`)**: Dynamically initiates an OAuth2 Client Credentials flow, retrieves, caches, and automatically refreshes access tokens, and uses mutual TLS (mTLS) client certificate verification to authenticate calls to partner bank REST APIs.

### 2. Message Queue AMQP Connector
- **RabbitMQ Connector (`RabbitMQBankConnector`)**: Subscribes asynchronously to CBS message queues (using `pika`) to ingest live transactions, with automatic fallback to a local mock interface if the message broker is unreachable.

### 3. Open Banking PSD2 Interface
- Exposes standard AISP endpoints (`/api/v1/psd2/accounts` and `/api/v1/psd2/transactions`) using Bearer JWT authentication for third-party access, validating user consent records prior to data dispatch.

### 4. Financial Message Parsers
- **ISO 20022 XML (`pacs.008.001.08`)**: Extracts transaction values, currencies, senders, and receivers from structured XML payment instructions.
- **SWIFT MT103**: Parses legacy text-based SWIFT blocks, fields (e.g. `:32A:` for amounts/currencies), and sender/receiver accounts.
- **SEPA Credit Transfers**: Ingests European credit transfer payloads mapped to standard transaction fields.

---

## 📄 AML Case Management Workflow Alignment (Phase 2 Task 7)

To satisfy national Financial Intelligence Unit (FIU) standards (e.g. FinCEN, MASAK) and support judicial admissibility:

### 1. SAR Filed Lifecycle Status
- Added `SAR_FILED` state to case management workflow.
- Allowed state transitions: `Escalated` -> `SAR Filed` and `SAR Filed` -> `Closed Confirmed`.

### 2. Automatic E-Filing Report Generation
- **FinCEN XML Compiler**: Transitions into `SAR_FILED` status trigger the `RegulatoryReporterService` to compile case details, timeline events, investigator notes, and suspect hashes into a fully schema-compliant FinCEN BSA Suspicious Activity Report (SAR) XML file.
- Files are persisted locally under `storage/regulatory_filings/` and exposed via secure FastAPI download endpoints (`/api/v1/cases/{case_id}/sar-report`).

### 3. Cryptographic Timeline Audit Chain
- Implemented sequential SHA-256 block hashing over case events:
  $$H_i = \text{SHA-256}(timestamp \mathbin{\Vert} type \mathbin{\Vert} description \mathbin{\Vert} actor \mathbin{\Vert} H_{i-1})$$
- Enforces an append-only, tamper-proof log of all investigator movements and status transitions. Changing or deleting any event breaks downstream block verification, ensuring audit credibility.

---

## 🔍 Full-Fledged AML Investigation Lifecycle (Phase 2 Task 8)

To support full-lineage auditing, secure dual-authorization, and role-based tracking:

### 1. Case Evidence Registry
- **Immutable Evidence Store**: Exposes a dedicated storage layer (`RedisStore("evidence")`) for document files, KYC profiles, and ledger proofs linked to investigation cases.
- **Cryptographic Content Hashing**: Enforces SHA-256 hashing of evidence contents upon registration. The hash is saved directly in the registry to guarantee chain-of-custody and prevent unauthorized modifications to investigation files.
- Exposed in the user interface under the Case Details page, allowing investigators to upload documents and view registered records with their hashes.

### 2. Multi-Signature Gating (Four-Eyes Principle)
- **Closure Validation**: Gated final case closure statuses (`CLOSED_CONFIRMED` and `CLOSED_FALSE_POSITIVE`) behind supervisor approval.
- **Secondary Signature Verification**: Status change API requests require a valid `supervisor_signature` key that must not be empty and must be different from the analyst actor's name.

### 3. Investigator Role Auditing
- **Compliance Activity Logging**: Active logs track analyst actions including case accesses (`access_case`), entity profile queries (`query_entity`), cross-bank resolution requests (`cross_bank_resolve`), and Private Set Intersection matching (`cross_bank_psi`).
- **Session Duration Tracking**: Logs session durations to detect anomalous queries or internal threats.
- Exposed in a real-time investigator activity audit trail grid at the bottom of the main Investigation Dashboard.

---

## 🤝 Consortium Incentive Mechanisms & Client Contribution Auditing (Phase 2 Task 22)

To align institutional incentives and enforce accountability in commercial federated anti-fraud network consortia:

### 1. Federated Shapley Value (SV) Estimation
- **Leave-One-Out (LOO) Shapley Evaluation**: At the end of a simulation, the coordinator automatically computes the marginal utility contribution of each participant bank.
- **Auditing Protocol**:
  1. Measures the baseline performance (F1-score) of the aggregate global model ($F_{\text{global}}$) on the shared global validation dataset.
  2. Aggregates subsets of client parameters excluding one client at a time (LOO model).
  3. Evaluates the LOO model to find its validation performance ($F_{-i}$).
  4. Calculates the marginal contribution score: $SV_i = F_{\text{global}} - F_{-i}$.

### 2. Free-Rider & Poisoning Detection (Quarantine Trigger)
- **Free-Rider Identification**: The auditing service monitors the variance of client parameter updates relative to the global model state. A client update with variance below $10^{-6}$ indicates zero-variance training (a client returning raw base weights or random noise to acquire global weights without training).
- **Poisoning Isolation**: If a client's marginal contribution score $SV_i \le -0.05$, it means including their updates significantly degrades the overall model accuracy, indicating malicious parameter poisoning.
- **Client Quarantine**: Flagged clients are dynamically set to `QUARANTINED` and their connection status becomes `ClientStatus.OFFLINE`. They are automatically excluded from participating in subsequent aggregation rounds.

### 3. Consortium Clearing Ledger
- Contribution scores are translated into relative payout weights on a virtual $100,000 USD incentive pool.
- Every contribution calculation and quarantine action is written as a signed cryptographic event to the immutable SHA-256 audit ledger (`immutable_audit_chain.py`) to prevent tampering and support settlement verification.

---

## 🔒 Hardware and Cryptographic Security Drivers (TEE & FHE)

To maximize the security of the collaborative AML platform, hardware and cryptographic isolation mechanisms have been added:

### 1. Trusted Execution Environment (TEE - Intel SGX / AWS Nitro)
- **Secure Memory Aggregation:** Raw model parameters from clients are collected as plaintext only within the isolated hardware memory regions (enclave) of the TEE. No actor outside the enclave, including the host operating system or hypervisor, can access these parameters.
- **Remote Attestation:** The integrity of the code running inside the enclave is verified using `MRENCLAVE` (code measurement) and `MRSIGNER` (signing authority) digests. Training rounds do not start unless the cryptographic signature verification is successful.

### 2. Fully Homomorphic Encryption (FHE - CKKS)
- **Computation on Encrypted Data:** Clients send their model updates encrypted with the FHE public key. The server aggregates these updates homomorphically (homomorphic average) directly over the ciphertexts without decrypting them. The server never observes plaintext parameters at any stage.
- **Noise and Dimension Management:** Performance/security tradeoffs are monitored dynamically via CKKS noise accumulation and key management simulation.


