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
