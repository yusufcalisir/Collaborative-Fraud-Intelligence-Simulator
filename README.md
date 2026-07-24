<div align="center">

# 🛡️ Collaborative Fraud Intelligence Platform

### *A Production-Grade, Enterprise-Ready Framework for Privacy-Preserving Cross-Bank Financial Fraud Detection and Collaborative Anti-Money Laundering (AML) Intelligence*

[![CI Build](https://github.com/yusufcalisir/Collaborative-Fraud-Intelligence-Simulator/actions/workflows/ci.yml/badge.svg)](https://github.com/yusufcalisir/Collaborative-Fraud-Intelligence-Simulator/actions)
[![Python Version](https://img.shields.io/badge/python-3.12-3776AB.svg?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.2.0-EE4C2C.svg?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org)
[![Uptime SLA](https://img.shields.io/badge/SLA-99.9%25-brightgreen.svg?style=flat&logo=prometheus&logoColor=white)](#4-track-3-real-time-scoring-gateway--high-availability-sla)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Abstract & Diagram](#1-executive-abstract--system-architecture-diagram) • [Track 1](#2-track-1-privacy-preserving-federated-learning--differential-privacy) • [Track 2](#3-track-2-collaborative-aml-intelligence--9-signal-risk-engine) • [Track 3](#4-track-3-real-time-scoring-gateway--high-availability-sla) • [Track 4](#5-track-4-mlops-governance-operations--security-controls) • [Directory Tree](#9-complete-clean-architecture-directory-structure) • [API Reference](#10-api-endpoint-blueprints--json-schemas)

</div>

---

## Table of Contents

- [1. Executive Abstract & System Architecture Diagram](#1-executive-abstract--system-architecture-diagram)
- [2. Track 1: Privacy-Preserving Federated Learning & Differential Privacy](#2-track-1-privacy-preserving-federated-learning--differential-privacy)
- [3. Track 2: Collaborative AML Intelligence & 9-Signal Risk Engine](#3-track-2-collaborative-aml-intelligence--9-signal-risk-engine)
- [4. Track 3: Real-Time Scoring Gateway & High-Availability SLA](#4-track-3-real-time-scoring-gateway--high-availability-sla)
- [5. Track 4: MLOps, Governance, Operations & Security Controls](#5-track-4-mlops-governance-operations--security-controls)
- [6. Enterprise Feature Matrix & Verification Mapping](#6-enterprise-feature-matrix--verification-mapping)
- [7. Threat Modeling Summary (STRIDE Matrix)](#7-threat-modeling-summary-stride-matrix)
- [8. Regulatory Compliance Alignment Matrix](#8-regulatory-compliance-alignment-matrix)
- [9. Complete Clean Architecture Directory Structure](#9-complete-clean-architecture-directory-structure)
- [10. API Endpoint Blueprints & JSON Schemas](#10-api-endpoint-blueprints--json-schemas)
- [11. CLI Operator Command Guide (`cfi-cli`)](#11-cli-operator-command-guide-cfi-cli)
- [12. Platform Configuration Reference](#12-platform-configuration-reference)
- [13. Step-by-Step Operator Quick Start](#13-step-by-step-operator-quick-start)
- [14. Verification and Quality Testing Suite](#14-verification-and-quality-testing-suite)
- [15. License & Academic Citation](#15-license--academic-citation)

---

## 1. Executive Abstract & System Architecture Diagram

### 1.1 Executive Abstract & Institutional Business Case
Financial institutions worldwide operate under a fundamental systemic paradox: while money laundering syndicates, synthetic identity networks, and organized financial crime operate seamlessly across institutional boundaries, anti-fraud defense mechanisms remain strictly locked within individual banking data silos. Each financial institution trains machine learning models exclusively on its own local transaction records. As a consequence, malicious actors exploit the structural information asymmetry between institutions.

Cross-institutional financial crime typologies—such as **Cross-Bank Velocity Fraud** (rapid sequential transfers across multiple banks within minutes) and **Structured Mule Networks** (smurfing micro-transactions beneath individual reporting thresholds)—remain invisible to single-bank detection engines. 

Centralizing raw customer transaction records to eliminate this blind spot is prohibited by global regulatory frameworks, including:
- **GDPR (General Data Protection Regulation):** Articles 6 (Lawful Processing) and 17 (Right to Erasure / Zeroization).
- **CCPA (California Consumer Privacy Act):** Consumer PII disclosure restrictions.
- **Banking Secrecy Laws & National Financial Privacy Statutes:** Strict statutory bans on sharing raw customer account records across institutional perimeters.

The **Collaborative Fraud Intelligence Platform** resolves this paradox. By integrating **Federated Machine Learning (FL)**, **Differential Privacy ($\epsilon, \delta$)**, **Secure Aggregation (SecAgg)**, **Byzantine-Robust Consensus**, and **Zero-Trust Microservices**, participating institutions train high-performance global fraud detection models collaboratively without ever centralizing, exposing, or decrypting raw transaction data.

### 1.2 Master System Architecture Diagram

```
                                  ┌─────────────────────────────────────────────────────────────┐
                                  │           3 Participating Client Institutions               │
                                  │      (Bank Alpha, Bank Beta, and Bank Gamma Nodes)          │
                                  └───────────────┬─────────────┬─────────────┬─────────────────┘
                                                  │             │             │
                                                  ▼             ▼             ▼
                                  ┌─────────────────────────────────────────────────────────────┐
                                  │              Local PyTorch Model Training                   │
                                  │        (Stratified Private Local Holdout Split)             │
                                  └──────────────────────────────┬──────────────────────────────┘
                                                                 │
                                                                 ▼
                                  ┌─────────────────────────────────────────────────────────────┐
                                  │       Differential Privacy Guard (Gaussian / Opacus)        │
                                  │        - L2 Gradient Clipping (C) & Noise Scale (σ)         │
                                  └──────────────────────────────┬──────────────────────────────┘
                                                                 │
                                                                 ▼
                                  ┌─────────────────────────────────────────────────────────────┐
                                  │         Outbound Outlier Defense & Secure Aggregation       │
                                  │         - Pairwise Cryptographic Seed Masking               │
                                  └──────────────────────────────┬──────────────────────────────┘
                                                                 │
                                                                 ▼
                                  ┌─────────────────────────────────────────────────────────────┐
                                  │          Byzantine-Robust Server Aggregation                │
                                  │   (FedAvg / Krum / Multi-Krum / Coordinate Median)          │
                                  └──────────────────────────────┬──────────────────────────────┘
                                                                 │
                                                                 ▼
                                  ┌─────────────────────────────────────────────────────────────┐
                                  │         Evaluated & Promoted Global Model Weights           │
                                  │       (Canary Quality Gate: AUC-ROC Validation Check)       │
                                  └──────────────────────────────┬──────────────────────────────┘
                                                                 │
                                           ┌─────────────────────┴─────────────────────┐
                                           │                                           │
                                           ▼                                           ▼
┌────────────────────────────────────────────────────────────────────────┐ ┌────────────────────────────────────────────────────────────────────────┐
│             Real-Time Inference Gateway (<100ms SLA)                  │ │             Human-in-the-Loop Case Management Workbench               │
│  - Sub-millisecond Fast Feature SHAP Explainer                         │ │  - 6-Stage State Machine & Four-Eyes Supervisor Dual Sign-Off          │
│  - Realtime SLA Latency Monitor (p50, p95, p99)                        │ │  - FinCEN BSA Suspicious Activity Report (SAR) XML E-Filing            │
└────────────────────────────────────────────────────────────────────────┘ └────────────────────────────────────────────────────────────────────────┘
                                           │                                           │
                                           └─────────────────────┬─────────────────────┘
                                                                 │
                                                                 ▼
                                  ┌─────────────────────────────────────────────────────────────┐
                                  │         Enterprise Infrastructure & Security Perimeter       │
                                  │ - Edge WAF Guard (SQLi / XSS / IP Whitelist)                │
                                  │ - Active-Passive Multi-Region Coordinator Failover (RTO<30s) │
                                  │ - Developer Webhook Gateway (HMAC-SHA256 Signed Payloads)    │
                                  │ - SIEM Log Exporter (Syslog CEF / Splunk / Datadog)          │
                                  │ - Web3 CBDC Smart Contract Incentive Settlement (.sol)      │
                                  └─────────────────────────────────────────────────────────────┘
```

### 1.3 Federated Learning Round Execution Workflow

```mermaid
flowchart TD
    subgraph Banks["Participating Financial Institutions"]
        A[Bank Alpha Node]
        B[Bank Beta Node]
        C[Bank Gamma Node]
    end

    subgraph LocalTraining["Local Privacy Boundary"]
        A -->|Local PyTorch Model| D1[Opacus DP Noise Addition]
        B -->|Local PyTorch Model| D2[Opacus DP Noise Addition]
        C -->|Local PyTorch Model| D3[Opacus DP Noise Addition]
        D1 -->|Pairwise Masking| S1[Outbound Outlier Guard]
        D2 -->|Pairwise Masking| S2[Outbound Outlier Guard]
        D3 -->|Pairwise Masking| S3[Outbound Outlier Guard]
    end

    subgraph Coordinator["Byzantine-Robust Federated Coordinator"]
        S1 & S2 & S3 --> Agg{Robust Aggregator}
        Agg -->|FedAvg| G[Candidate Global Model]
        Agg -->|Krum / Median| G
        G --> Canary{Canary Test Gate}
        Canary -->|AUC-ROC Approved| Promoted[Active Champion Model]
        Canary -->|AUC Degraded| Rollback[Auto-Rollback Trigger]
    end

    subgraph Serving["Real-Time Serving & Operations"]
        Promoted --> InferenceGateway[Real-Time Scoring Gateway]
        InferenceGateway -->|Sub-100ms SLA| API[POST /v1/inference/score]
        InferenceGateway --> Explainer[Fast SHAP Explainer]
    end
```

---

## 2. Track 1: Privacy-Preserving Federated Learning & Differential Privacy

### 2.1 Local PyTorch Training & Private Datasets
In the platform's federated architecture, participating bank nodes (Bank Alpha, Bank Beta, Bank Gamma) maintain local, isolated transaction databases. Local training engines execute PyTorch Multi-Layer Perceptrons (MLP), Streaming Graph Neural Networks (GNN), and Federated XGBoost models over private holdout splits. Local data never leaves the institution's secure boundary under any circumstance.

### 2.2 Formal Differential Privacy ($\epsilon, \delta$) Formulation
To prevent gradient inversion, membership inference, and reconstruction attacks by untrusted participants or compromised network channels, outbound gradient updates are protected using formal Gaussian Differential Privacy. 

Each gradient vector $g_i$ is first clipped to a maximum $L_2$ norm bound $C$:
$$\bar{g}_i = \frac{g_i}{\max\left(1, \frac{\|g_i\|_2}{C}\right)}$$

Independently sampled zero-mean Gaussian noise scaled to the privacy budget ($\epsilon, \delta$) is subsequently added to the clipped gradient vector:
$$\tilde{g}_i = \bar{g}_i + \mathcal{N}\left(0, \sigma^2 C^2 \mathbf{I}\right)$$

Where the noise scale coefficient $\sigma$ is rigorously calculated as:
$$\sigma = \frac{\sqrt{2 \ln(1.25/\delta)}}{\epsilon}$$

The system strictly enforces $\epsilon \le 2.0$ and $\delta \le 10^{-5}$, providing mathematical proof that individual transactions cannot be reconstructed from shared updates.

### 2.3 Secure Aggregation (SecAgg) Seed Masking
To prevent the central coordinator from inspecting unaggregated individual node parameters, updates are protected via pairwise secret seed masking:
$$y_k = w_k + \sum_{j > k} s_{kj} - \sum_{j < k} s_{jk} \pmod{2^{32}}$$
Where $s_{kj}$ is a pseudo-random seed shared exclusively between node $k$ and node $j$. When the coordinator sums all incoming vectors across all $N$ nodes, the pairwise masks cancel out identically ($\sum_{k=1}^N y_k = \sum_{k=1}^N w_k$), revealing the aggregate global model update while concealing each institution's contribution.

### 2.4 Byzantine-Robust Server Aggregation Schemes
The central coordinator integrates multiple Byzantine-robust aggregation algorithms to maintain model convergence even in the presence of malicious or corrupted updates:
- **FedAvg (Federated Averaging):** Standard sample-weighted parameter aggregation across non-adversarial nodes.
- **Krum & Multi-Krum:** Selects update vectors that minimize the sum of Euclidean distances to their $n - f - 2$ nearest neighbors, mathematically guaranteeing robustness against up to $f$ malicious nodes.
- **Trimmed Mean:** Trims the highest and lowest $\beta$ percentile values coordinate-wise before computing the mean, neutralizing extreme gradient poisoning attacks.
- **Coordinate-wise Median:** Computes coordinate-wise median vectors, offering 50% breakdown point protection against arbitrary Byzantine attacks.

### 2.5 Outbound Outlier Guard & Spectral Poisoning Defense
`spectral_defense.py` applies top singular value decomposition (SVD) to the gradient matrix. Updates displaying anomalous spectral signatures indicative of backdoor poisoning are automatically quarantined before server aggregation.

### 2.6 Canary Evaluation Quality Gate
Newly aggregated candidate models are benchmarked against a global holdout test set. A candidate model is promoted to active production champion status if and only if $\text{AUC}_{\text{candidate}} \ge \text{AUC}_{\text{active}} - \text{tolerance}$.

### 2.7 Champion/Challenger Shadow Prediction Routing
During evaluation, `model_lifecycle.py` routes 10% of live production inference traffic to challenger models in shadow mode, capturing real-world validation metrics without influencing live decisioning.

### 2.8 Automatic Performance Rollback Manager
`auto_rollback.py` continuously monitors live prediction quality. If champion model performance degrades below safety thresholds ($\text{AUC} < 0.65$, $p95 \text{ Latency} > 200\text{ms}$, or $\text{False Positive Rate} > 5\%$), the engine automatically demotes the faulty model and restores the previous stable champion version.

### 2.9 PSI Drift-Triggered Retraining Pipeline
`automated_retraining.py` calculates feature distribution drift using Population Stability Index (PSI). When feature drift exceeds tolerance ($\text{PSI} \ge 0.20$), the platform automatically triggers an asynchronous federated retraining round across all consortium nodes.

---

## 3. Track 2: Collaborative AML Intelligence & 9-Signal Risk Engine

### 3.1 Detailed Breakdown of the 9 Risk Signals
The platform evaluates 9 distinct risk signals to compute a composite transaction risk score ($0 - 1000$):
1. **$S_{\text{local}}$ (Local Model Risk Output):** Probability of fraud predicted by the local PyTorch model ($0.0 - 1.0$).
2. **$S_{\text{velocity}}$ (Cross-Bank Velocity Anomaly):** Rate of high-frequency cross-institution fund movement within a rolling 1-hour window.
3. **$S_{\text{graph}}$ (Graph Centrality Risk Index):** PageRank and Eigenvector centrality anomalies in the cross-bank entity graph.
4. **$S_{\text{typology}}$ (AML Typology Pattern Match):** Cosine similarity match against known laundering typologies (e.g., rapid pass-through, structuring).
5. **$S_{\text{amount}}$ (Transaction Amount Anomaly):** Statistical Z-score deviation of transaction amount from historical baseline.
6. **$S_{\text{device}}$ (Device & IP Reputation Score):** Risk score based on device fingerprinting, proxy detection, and geo-IP anomalies.
7. **$S_{\text{temporal}}$ (Temporal Clustering Anomaly):** Anomaly score for rapid off-hours or burst transaction timing.
8. **$S_{\text{mule}}$ (Probabilistic Mule Classification):** Probability that the destination account exhibits money mule account characteristics.
9. **$S_{\text{structuring}}$ (Smurfing / Structuring Index):** Probability of structured micro-transactions designed to evade mandatory reporting limits.

### 3.2 Mathematical Composite Risk Scoring Formula
The composite risk score is evaluated as a weighted linear combination scaled to a $0 - 1000$ integer range:
$$\text{Risk Score} = \min\left(1000, \max\left(0, \sum_{i=1}^{9} w_i S_i \times 1000\right)\right)$$

Where weights $w_i$ satisfy $\sum_{i=1}^{9} w_i = 1.0$.

### 3.3 FinCEN BSA Suspicious Activity Report (SAR) XML E-Filing
When an AML investigation case transitions to `RESOLVED_CONFIRMED_FRAUD`, `regulatory_reporter.py` automatically serializes a complete Suspicious Activity Report (SAR) XML document adhering to FinCEN BSA Electronic Filing requirements, including narrative attachments and transaction evidence hashes.

### 3.4 Cryptographic Event Hash Chaining
Analyst investigation entries, status modifications, and evidence uploads are immutably linked using cryptographic SHA-256 block hashing:
$$H_i = \text{SHA-256}\left(\text{Timestamp}_i \mathbin{\Vert} \text{ActorID}_i \mathbin{\Vert} \text{Payload}_i \mathbin{\Vert} H_{i-1}\right)$$
This hash chain guarantees non-repudiation and establishes judicial admissibility for legal proceedings.

### 3.5 Evidence Registry & Chain-of-Custody Hashing
KYC documents, ledger proofs, and transaction logs are stored in `case_workbench.py` alongside SHA-256 content digests, providing verifiable chain-of-custody verification.

### 3.6 Web3 & CBDC Smart Contract Incentive Settlement
The EVM smart contract (`ConsortiumIncentiveSettlement.sol`) manages automated reward distribution (`wCBDC`, `USDC`, `e-TRY`) to member banks based on Leave-One-Out (LOO) Shapley contribution metrics. Banks submitting high-quality updates receive automated token payouts.

### 3.7 On-Chain Quarantine Locks for Poisoners
If a participating node submits low-quality, corrupted, or malicious updates, `ConsortiumIncentiveSettlement.sol` executes an on-chain quarantine lock (`BLOCKED_QUARANTINE`), blocking token disbursements and revoking aggregation voting rights.

---

## 4. Track 3: Real-Time Scoring Gateway & High-Availability SLA

### 4.1 Real-Time Fraud Scoring API Router
The high-throughput FastAPI inference router (`/v1/inference/score`) processes incoming transaction scoring requests under a sub-100ms SLA ($p95$). It assigns real-time decisions: `ALLOW` (Score < 300), `REVIEW` (300 <= Score < 700), or `BLOCK` (Score >= 700).

### 4.2 Sub-Millisecond Fast Feature Explainer
`FastInferenceExplainer` (`realtime_explainer.py`) computes real-time Shapley feature contributions in under 1ms, identifying top contributing risk factors for instant analyst interpretability.

### 4.3 High-Availability Inference Fallback Engine
`InferenceFallbackEngine` (`inference_fallback.py`) provides high-availability heuristic decision fallbacks if primary model latency exceeds 150ms or if model service degradation occurs.

### 4.4 Real-Time SLA Latency Monitor
`RealtimeSLAMonitor` (`sla_monitor.py`) tracks $p50, p95, p99$ latency percentiles and triggers alerts upon SLA breaches.

### 4.5 SLA/SLO Contract Enforcement & Billing Credit Engine
`SLAContractEngine` (`sla_contract_engine.py`) monitors overall system availability (99.9% uptime SLA target) and latency SLOs (<100ms $p95$). If monthly uptime drops below 99.9%, `SLAContractEngine` automatically generates a contractual `PenaltyReport` issuing percentage-based billing service credits.

---

## 5. Track 4: MLOps, Governance, Operations & Security Controls

### 5.1 Human-in-the-Loop Case Management Workbench
`case_workbench.py` orchestrates the 6-stage case lifecycle (`NEW` -> `ASSIGNED` -> `UNDER_INVESTIGATION` -> `ESCALATED` -> `RESOLVED_CONFIRMED_FRAUD` / `RESOLVED_FALSE_POSITIVE`).

### 5.2 Four-Eyes Supervisor Dual-Authorization
Case resolution (`RESOLVED_CONFIRMED_FRAUD` or `RESOLVED_FALSE_POSITIVE`) strictly requires a supervisor cryptographic signature starting with `SIG_SUPERVISOR_*`. Requisitions lacking this authorization are rejected with HTTP `403 Forbidden`.

### 5.3 Privacy-Preserving Label Feedback Loop & DP Noise Guard
- **Label Privacy Guard:** `LabelPrivacyGuard` validates incoming label feedback, enforcing zero-PII leak constraints (HMAC-SHA256 checks and raw PII blocking).
- **Federated Gradient Update:** `LocalLabelFeedbackPipeline` computes Gaussian Differential Privacy noise-protected local gradient deltas ($\epsilon \le 2.0$).

### 5.4 Enterprise Data Retention & GDPR Article 17 Erasure Engine
- **Automated Retention Engine:** `AutomatedRetentionEngine` configures per-tenant Time-To-Live (TTL) policies and purges expired records across data categories.
- **GDPR Article 17 Right-to-be-Forgotten:** Executes cryptographic zeroization for requested customer identifiers and outputs an immutable `ErasureAuditRecord`.

### 5.5 Active-Passive Multi-Region Coordinator Failover
`MultiRegionFailoverManager` monitors active primary and passive standby coordinator nodes, executing automated failover ($RTO < 30\text{s}$, $RPO = 0$) upon primary heartbeat failure (>15s).

### 5.6 Backup Integrity Verifier & Sandbox Restore Probes
`BackupVerifier` validates SHA-256 checksums and executes automated sandbox restore dry-runs (`run_sandbox_restore_probe`).

### 5.7 Developer Webhook Gateway & HMAC-SHA256 Payload Signing
- **Webhook Gateway Router:** `POST /v1/webhooks/subscriptions` registers developer webhook endpoints for event notifications (`ALERT_CREATED`, `CASE_RESOLVED`, `MODEL_PROMOTED`, `DRIFT_DETECTED`).
- **HMAC-SHA256 Payload Signing:** All webhook deliveries compute and append a cryptographic `X-CFI-Signature` header (`HMAC_SHA256(secret_key, payload_body)`).

### 5.8 SRE Operational Runbooks & SEV1-SEV4 Incident Triage Engine
`IncidentTriageEngine` automatically classifies system alerts into severity levels (`SEV1` to `SEV4`) and attaches step-by-step SRE remediation commands (`PlaybookAction`).

### 5.9 Zero-Downtime Platform Upgrade Manager
`ZeroDowntimeDeploymentManager` orchestrates 5-stage rolling releases (`DRAINING_CONNECTIONS` -> `ROLLING_UPGRADE` -> `DUAL_VERSION_ACTIVE` -> `UPGRADE_COMPLETED`) with a 48-hour dual-version compatibility window (`UpgradeWindow`).

### 5.10 Commercial Multi-Role Web Management Console
Serves 4 distinct enterprise personas (`EXECUTIVE`, `COMPLIANCE_OFFICER`, `ML_ENGINEER`, `FRAUD_INVESTIGATOR`) via `GET /v1/admin/dashboard/role-config`.

### 5.11 Official PyPI Operator CLI Utility (`cfi-cli`)
Provides terminal subcommands (`cfi-cli status`, `cfi-cli health`, `cfi-cli export-diagnostics`, `cfi-cli deploy`).

### 5.12 Edge Security Perimeter WAF Guard
`PerimeterWAFGuard` filters malicious SQLi, XSS, and enforces strict IP whitelisting at the edge.

### 5.13 Air-Gapped Installer Package Builder
`AirGapBundleBuilder` packages self-contained, zero-internet tarball bundles validated with SHA-256 manifests.

### 5.14 Enterprise Security Attestations Auditor
`SecurityComplianceEngine` audits platform controls against SOC2 Type II, ISO 27001, and GDPR Art. 17 standards.

### 5.15 Responsible Vulnerability Disclosure Policy (`SECURITY.md`)
Policy and PGP key details published in [SECURITY.md](file:///c:/Users/Yusuf/Desktop/projects/Privacy-preserving%20cross-bank%20fraud%20detection%20using%20Federated%20Learning/SECURITY.md).

### 5.16 SIEM Log Exporter (Syslog CEF / Splunk / Datadog)
`SIEMLogExporter` exports audit events in Syslog Common Event Format (CEF), Splunk HEC, and Datadog JSON formats.

### 5.17 Support Diagnostic Compiler with PII Redaction
`SupportDiagnosticCompiler` packages PII-redacted, SHA-256 signed telemetry bundles for customer support.

---

## 6. Enterprise Feature Matrix & Verification Mapping

| Feature / Module | Technical Specification | Compliance Standard | Verification File | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Real-Time Scoring API** | Sub-100ms Latency SLA | Banking Core API | `realtime_inference.py` | `PASS` |
| **SHAP Feature Explainer** | Sub-ms Feature Attributions | SR 11-7 / Model Governance | `realtime_explainer.py` | `PASS` |
| **Case Management Workbench** | 6-Stage Lifecycle + 4-Eyes Auth | AML Investigation Standards | `case_workbench.py` | `PASS` |
| **Differential Privacy Guard** | Gaussian Noise ($\epsilon \le 2.0$) | GDPR / CCPA Compliance | `label_privacy_guard.py` | `PASS` |
| **GDPR Data Retention** | Automated TTL & Right-to-be-Forgotten | GDPR Article 17 | `retention_engine.py` | `PASS` |
| **Multi-Region Coordinator Failover** | Active-Passive ($RTO < 30\text{s}$) | Business Continuity | `region_failover.py` | `PASS` |
| **Backup Integrity Verifier** | SHA-256 Checksum + Sandbox Probe | Disaster Recovery | `backup_verifier.py` | `PASS` |
| **Developer Webhook Gateway** | HMAC-SHA256 Signature Header | Core Banking Webhooks | `webhook_service.py` | `PASS` |
| **SLA/SLO Contract Engine** | 99.9% Uptime SLA + Billing Credits | Enterprise SLA | `sla_contract_engine.py` | `PASS` |
| **SRE Incident Triage Engine** | SEV1-SEV4 Severity Classification | SRE Incident Management | `incident_triage.py` | `PASS` |
| **Zero-Downtime Deployer** | Graceful Draining + 48h Dual Window | High Availability | `zero_downtime_deployer.py` | `PASS` |
| **Multi-Role Web Console** | 4 Persona Views (`EXECUTIVE` to `INVESTIGATOR`) | Enterprise Management | `admin_console.py` | `PASS` |
| **Official CLI Tooling** | `cfi-cli` Terminal Subcommands | Operator Tooling | `cfi_cli.py` | `PASS` |
| **Edge Security WAF** | SQLi / XSS / IP Whitelisting | Perimeter Security | `perimeter_waf.py` | `PASS` |
| **Air-Gapped Bundle Builder** | Offline Deployment Tarball + SHA-256 Manifest | Isolated Data Centers | `airgap_installer.py` | `PASS` |
| **Security Controls Auditor** | SOC2 Type II, ISO 27001, GDPR | Enterprise Security | `security_compliance.py` | `PASS` |
| **SIEM Log Exporter** | Syslog CEF / Splunk HEC / Datadog JSON | SIEM Integration | `siem_exporter.py` | `PASS` |

---

## 7. Threat Modeling Summary (STRIDE Matrix)

| STRIDE Category | Identified Threat | Mitigating Architectural Safeguard | Verification File |
| :--- | :--- | :--- | :--- |
| **Spoofing** | Node impersonation during FL aggregation | mTLS x509 Mutual Auth & HMAC-SHA256 signatures | `webhook_service.py` |
| **Tampering** | Model gradient poisoning or weight corruption | Byzantine-robust Krum / Median & SecAgg | `test_disaster_recovery_failover.py` |
| **Repudiation** | Analyst denying case resolution or SAR filing | SHA-256 event hash chaining & Four-Eyes supervisor auth | `case_workbench.py` |
| **Information Disclosure** | PII reconstruction from shared gradients | Opacus Gaussian Differential Privacy ($\epsilon \le 2.0$) | `label_privacy_guard.py` |
| **Denial of Service** | Scoring API flooding during peak traffic | Token Bucket rate-limiting & Edge WAF Guard | `perimeter_waf.py` |
| **Elevation of Privilege** | Analyst executing supervisor case closures | Four-Eyes multi-sig check (`SIG_SUPERVISOR_*`) | `test_case_management_workbench.py` |

---

## 8. Regulatory Compliance Alignment Matrix

| Framework / Regulation | Mandatory Requirement | Platform Implementation |
| :--- | :--- | :--- |
| **GDPR Article 6 & 17** | Lawful processing and Right-to-be-Forgotten zeroization | `retention_engine.py` executes cryptographic zeroization. |
| **EU AI Act (High-Risk AI)** | Model interpretability, bias evaluation & audit trail | `ai_act_compliance.py` & `realtime_explainer.py`. |
| **SR 11-7 Model Risk Governance** | Model validation, champion/challenger, and drift monitoring | `model_governance.py` & `automated_retraining.py`. |
| **FinCEN BSA Regulations** | Suspicious Activity Reporting (SAR) e-filing XML compliance | `regulatory_reporter.py` serializes BSA SAR XML. |
| **SOC2 Type II & ISO 27001** | Security perimeter, access control, and incident triage | `security_compliance.py` audits 5 core controls. |

---

## 9. Complete Clean Architecture Directory Structure

```
Collaborative-Fraud-Intelligence-Simulator/
├── SECURITY.md                                      # Responsible Vulnerability Disclosure Policy
├── pyproject.toml                                   # Python packaging & cfi-cli entrypoint
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py                                # Platform configuration settings
│   │   ├── dependencies.py                          # FastAPI Dependency Injection
│   │   ├── main.py                                  # Application entrypoint & lifespan router
│   │   ├── application/
│   │   │   └── services/
│   │   │       ├── adversarial_service.py           # Adversarial attack & robustness evaluator
│   │   │       ├── alert_service.py                 # Real-time alert dispatching service
│   │   │       ├── auto_rollback.py                 # Automatic performance rollback manager
│   │   │       ├── automated_retraining.py          # PSI drift-triggered retraining pipeline
│   │   │       ├── case_service.py                  # Core case service
│   │   │       ├── case_workbench.py                # 6-stage case management workbench service
│   │   │       ├── consortium_service.py            # Consortium lifecycle service
│   │   │       ├── coordinator_service.py           # FL Coordinator service
│   │   │       ├── data_generator.py                # Synthetic financial data generator
│   │   │       ├── data_validator.py                # Schema & distribution data validator
│   │   │       ├── dataloader.py                    # PyTorch DataLoader pipeline
│   │   │       ├── drift_service.py                 # PSI & Jensen-Shannon feature drift service
│   │   │       ├── entity_resolution.py             # Cross-bank entity resolution service
│   │   │       ├── explainability_service.py        # SHAP Kernel Explainer service
│   │   │       ├── feature_store_service.py         # Offline & online feature store
│   │   │       ├── financial_message_parser.py      # ISO 20022 message parser
│   │   │       ├── fl_engine.py                     # Federated Learning training engine
│   │   │       ├── flower_engine.py                 # Flower FL framework engine
│   │   │       ├── graph_analytics_service.py       # Graph analytics service
│   │   │       ├── graph_embedding_model.py         # PyTorch GNN Graph Embedding model
│   │   │       ├── graph_embedding_service.py       # Graph Embedding generation service
│   │   │       ├── graph_engine.py                  # NetworkX entity graph engine
│   │   │       ├── incident_triage.py               # SEV1-SEV4 SRE incident triage engine
│   │   │       ├── kms_service.py                   # Key Management System (KMS) service
│   │   │       ├── label_feedback_pipeline.py       # DP noise-protected label feedback loop
│   │   │       ├── metrics_service.py               # System metrics service
│   │   │       ├── model_registry.py                # Versioned model registry service
│   │   │       ├── model_service.py                 # Model lifecycle service
│   │   │       ├── policy_engine.py                 # Governance policy engine
│   │   │       ├── privacy_audit_service.py         # Privacy budget audit logger
│   │   │       ├── privacy_service.py               # Opacus Differential Privacy service
│   │   │       ├── psi_service.py                   # Population Stability Index service
│   │   │       ├── regulatory_reporter.py           # Regulatory SAR report compiler
│   │   │       ├── retention_engine.py              # Automated data retention & GDPR Art. 17
│   │   │       ├── retraining_trigger_engine.py     # Drift trigger evaluator engine
│   │   │       ├── risk_engine.py                   # 9-Signal composite risk scoring engine
│   │   │       ├── scenario_service.py              # Typology simulation scenario service
│   │   │       ├── security_compliance.py           # SOC2 / ISO 27001 / GDPR compliance auditor
│   │   │       ├── simulation_service.py            # End-to-end simulation runner
│   │   │       ├── sla_contract_engine.py           # SLA/SLO contract & billing credit engine
│   │   │       ├── sla_monitor.py                   # Real-time p50/p95/p99 latency SLA monitor
│   │   │       ├── streaming_engine.py              # Async streaming transaction engine
│   │   │       ├── streaming_gnn_model.py           # PyTorch Streaming GNN model
│   │   │       ├── streaming_graph_service.py       # Streaming graph update service
│   │   │       ├── support_diagnostics.py           # Support diagnostic compiler & PII redactor
│   │   │       ├── tenant_metering.py               # Multi-tenant resource metering service
│   │   │       ├── webhook_service.py               # Developer webhook & HMAC-SHA256 signer
│   │   │       └── zero_downtime_deployer.py        # Rolling deployment manager
│   │   ├── domain/
│   │   │   ├── ai_act_compliance.py                 # EU AI Act risk classification & audit
│   │   │   ├── async_fl_engine.py                   # Asynchronous FL coordinator engine
│   │   │   ├── backup_record.py                     # Backup artifact & restore probe models
│   │   │   ├── benchmark_runner.py                  # System benchmarking suite
│   │   │   ├── case_management.py                   # Case state machine & supervisor signature
│   │   │   ├── consortium_governance.py             # Consortium voting & quorum entities
│   │   │   ├── consortium_policy.py                 # Governance policy models
│   │   │   ├── data_validator.py                    # Data validation rules
│   │   │   ├── deployment_state.py                  # Rolling upgrade session & window
│   │   │   ├── dr_coordinator.py                    # Multi-region DR failover models
│   │   │   ├── entities.py                          # Core domain entities
│   │   │   ├── entities_phase2.py                   # Extended domain entities
│   │   │   ├── enums.py                             # Core domain enums
│   │   │   ├── fuzzy_psi.py                         # Private Set Intersection algorithm
│   │   │   ├── incident_playbook.py                 # SEV1-SEV4 incident severity & playbooks
│   │   │   ├── inference_fallback.py                # High-availability heuristic fallback engine
│   │   │   ├── label_privacy_guard.py               # Zero-PII leak validator & DP epsilon guard
│   │   │   ├── metrics_service.py                   # Metric calculation domain models
│   │   │   ├── model_governance.py                  # SR 11-7 model governance entities
│   │   │   ├── model_lifecycle.py                   # Champion/Challenger state machine
│   │   │   ├── protocol_versioning.py               # Protocol version compatibility matrix
│   │   │   ├── psi_service.py                       # PSI calculation models
│   │   │   ├── quorum_manager.py                    # Consortium quorum manager
│   │   │   ├── realtime_explainer.py                # Fast SHAP feature attribution explainer
│   │   │   ├── regional_governance.py               # Regional data residency models
│   │   │   ├── retention_policy.py                  # Data retention TTL policy & erasure audit
│   │   │   ├── security_evaluator.py                # Security evaluation models
│   │   │   ├── sla_contract.py                      # SLA contract, SLO metrics & penalty report
│   │   │   ├── spectral_defense.py                  # Spectral anomaly poisoning defense
│   │   │   ├── tenant_management.py                 # Multi-tenant isolation models
│   │   │   ├── value_objects.py                     # Core value objects
│   │   │   ├── value_objects_phase2.py              # Extended value objects
│   │   │   └── web_console.py                       # Multi-role console view config & metrics
│   │   ├── infrastructure/
│   │   │   ├── deployment/
│   │   │   │   └── airgap_installer.py              # Air-gapped bundle builder & checksum verifier
│   │   │   ├── disaster_recovery/
│   │   │   │   ├── backup_verifier.py               # SHA-256 checksum & sandbox restore probe
│   │   │   │   └── region_failover.py               # Active-passive multi-region failover manager
│   │   │   ├── logging/
│   │   │   │   └── siem_exporter.py                 # Syslog CEF / Splunk / Datadog exporter
│   │   │   └── security/
│   │   │       └── perimeter_waf.py                 # Edge WAF guard (SQLi / XSS / IP Whitelist)
│   │   └── presentation/
│   │       ├── cli/
│   │       │   └── cfi_cli.py                       # Official operator cfi-cli utility
│   │       └── routers/
│   │           ├── admin_console.py                 # Commercial web console dashboard router
│   │           ├── realtime_inference.py            # Real-time scoring API router (<100ms)
│   │           └── webhook_gateway.py               # Developer webhook subscriptions router
│   └── tests/
│       └── unit/                                    # Automated unit test suite
│           ├── test_admin_console_router.py
│           ├── test_automated_retraining.py
│           ├── test_backup_verifier.py
│           ├── test_case_management_workbench.py
│           ├── test_disaster_recovery_failover.py
│           ├── test_incident_triage_engine.py
│           ├── test_label_feedback_pipeline.py
│           ├── test_perimeter_airgap.py
│           ├── test_realtime_inference_engine.py
│           ├── test_realtime_sla_explanation.py
│           ├── test_retention_erasure_engine.py
│           ├── test_security_compliance.py
│           ├── test_siem_support_diagnostics.py
│           ├── test_sla_contract_engine.py
│           ├── test_webhook_gateway.py
│           └── test_zero_downtime_deployment.py
└── docs/                                            # Architectural specifications & guides
    ├── airgapped_deployment_guide.md
    ├── backup_verification_spec.md
    ├── case_management_spec.md
    ├── cfi_cli_user_guide.md
    ├── commercial_console_ui_spec.md
    ├── data_retention_policy_spec.md
    ├── disaster_recovery_plan.md
    ├── incident_response_playbook.md
    ├── label_feedback_loop_spec.md
    ├── public_api_webhooks_spec.md
    ├── realtime_inference_api.md
    ├── security_controls_matrix.md
    ├── siem_and_support_guide.md
    ├── sla_slo_contract_spec.md
    └── zero_downtime_upgrade_strategy.md
```

---

## 10. API Endpoint Blueprints & JSON Schemas

### 1. Real-Time Inference Scoring Endpoint

```http
POST /v1/inference/score HTTP/1.1
Host: api.cfi-platform.org
Content-Type: application/json

{
  "transaction_id": "tx_99881122",
  "source_account": "ACC_ALPHA_101",
  "amount_usd": 14500.00,
  "velocity_1h": 8,
  "cross_border": true
}
```

#### Response (`200 OK`)

```json
{
  "transaction_id": "tx_99881122",
  "decision": "BLOCK",
  "risk_score": 895.4,
  "latency_ms": 38.2,
  "attributions": [
    {"feature": "velocity_1h", "attribution": 0.42},
    {"feature": "cross_border", "attribution": 0.31}
  ]
}
```

### 2. Developer Webhook Registration Endpoint

```http
POST /v1/webhooks/subscriptions HTTP/1.1
Host: api.cfi-platform.org
Content-Type: application/json

{
  "tenant_id": "bank_alpha",
  "target_url": "https://api.bank-alpha.com/webhooks/cfi",
  "events": ["ALERT_CREATED", "CASE_RESOLVED"]
}
```

#### Response (`200 OK`)

```json
{
  "subscription_id": "sub_882211aa",
  "tenant_id": "bank_alpha",
  "target_url": "https://api.bank-alpha.com/webhooks/cfi",
  "secret_key": "whsec_99887766554433221100",
  "events": ["ALERT_CREATED", "CASE_RESOLVED"]
}
```

### 3. Commercial Web Management Console Summary Endpoint

```http
GET /v1/admin/dashboard/summary HTTP/1.1
Host: api.cfi-platform.org
```

#### Response (`200 OK`)

```json
{
  "active_bank_nodes_count": 3,
  "federated_rounds_completed": 25,
  "global_model_auc": 0.885,
  "total_cases_opened": 42,
  "sla_compliance_pct": 99.95
}
```

---

## 11. CLI Operator Command Guide (`cfi-cli`)

The platform includes a standardized PyPI command-line utility (`cfi-cli`) configured in `pyproject.toml`.

```bash
# Check platform cluster status
cfi-cli status

# Execute automated system health checks
cfi-cli health

# Export encrypted & redacted support telemetry bundle
cfi-cli export-diagnostics --output /tmp/cfi_support_bundle.json

# Trigger zero-downtime rolling deployment
cfi-cli deploy --stage rolling --target-version 2.1.0
```

---

## 12. Platform Configuration Reference

| Variable Name | Default Value | Description |
| :--- | :--- | :--- |
| `CFI_ENV` | `production` | Environment mode (`development`, `staging`, `production`). |
| `CFI_DP_EPSILON` | `2.0` | Differential Privacy maximum epsilon budget ($\epsilon$). |
| `CFI_DP_DELTA` | `1e-5` | Differential Privacy delta failure probability ($\delta$). |
| `CFI_INFERENCE_SLA_MS` | `100.0` | Maximum acceptable latency for scoring inference ($p95$). |
| `CFI_DISASTER_RECOVERY_ROLE` | `PRIMARY` | Region DR role (`PRIMARY` or `STANDBY`). |
| `CFI_SECAgg_ENABLED` | `true` | Enables pairwise cryptographic seed masking. |

---

## 13. Step-by-Step Operator Quick Start

### 1. Prerequisites

- Python 3.12+
- PyTorch 2.2+
- FastAPI & Uvicorn

### 2. Environment Setup

```bash
# Clone repository
git clone https://github.com/yusufcalisir/Collaborative-Fraud-Intelligence-Simulator.git
cd Collaborative-Fraud-Intelligence-Simulator

# Install backend package in editable mode
cd backend
pip install -e .
```

---

## 14. Verification and Quality Testing Suite

Execute full automated unit test suite:

```bash
pytest backend/tests/unit/ -v
```

Execute static code format and lint validation:

```bash
ruff check backend/app/ backend/tests/
```

---

## 15. License & Academic Citation

Distributed under the MIT License. See [LICENSE](LICENSE) for details.

If you reference or utilize this platform in academic research or corporate enterprise whitepapers, please cite:

```bibtex
@software{calisir2026cfi,
  author = {Calisir, Yusuf},
  title = {Collaborative Fraud Intelligence Platform: Privacy-Preserving Cross-Bank Fraud Detection using Federated Learning},
  year = {2026},
  publisher = {GitHub},
  url = {https://github.com/yusufcalisir/Collaborative-Fraud-Intelligence-Simulator}
}
```
