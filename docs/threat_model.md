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

### 2.3 Model Memorization

**Threat**: The trained model memorizes and leaks specific transactions.

**Mitigation**: The MLP architecture with dropout (0.3, 0.2) and batch normalization reduces overfitting. DP noise further prevents memorization of individual examples.

---

## 3. Integrity Threats

### 3.1 Model Poisoning

**Threat**: A compromised bank sends malicious model updates to degrade the global model or introduce a backdoor.

**Status in simulator**: Not mitigated. This is a known limitation.

**Production mitigations**:
- Robust aggregation methods (Krum, trimmed mean, coordinate-wise median)
- Anomaly detection on update norms
- Byzantine fault-tolerant protocols

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

**Note**: Basic sequential composition is used. Advanced composition (Rényi DP, moments accountant) would yield tighter bounds. In production, use the `opacus` library for rigorous privacy accounting.

---

## 6. Gap Analysis — Simulator vs Production

| Security Property | Simulator | Production Target |
|---|---|---|
| Transport encryption | None (localhost) | TLS 1.3 mutual auth |
| Client authentication | None | mTLS + API keys |
| Secure aggregation | Simulated pairwise masks | MPC (SPDZ, SecureNN) |
| DP accounting | Basic composition | Rényi DP (moments accountant) |
| Byzantine resilience | None | Krum / Trimmed Mean |
| Audit logging | Console logging | Tamper-evident audit trail |
| Key management | None | HSM-backed key infrastructure |

This gap analysis is intentional — the simulator demonstrates the concepts. Production deployment requires hardening each layer.
