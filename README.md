<div align="center">

# 🛡️ Collaborative Fraud Intelligence Platform

### *Enterprise-Grade, Privacy-Preserving Cross-Bank Financial Fraud Detection & Collaborative Anti-Money Laundering (AML) Intelligence*

[![CI Build](https://github.com/yusufcalisir/Collaborative-Fraud-Intelligence-Simulator/actions/workflows/ci.yml/badge.svg)](https://github.com/yusufcalisir/Collaborative-Fraud-Intelligence-Simulator/actions)
[![Python Version](https://img.shields.io/badge/python-3.12-3776AB.svg?style=flat&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.2.0-EE4C2C.svg?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org)
[![Uptime SLA](https://img.shields.io/badge/SLA-99.9%25-brightgreen.svg?style=flat&logo=prometheus&logoColor=white)](#-real-time-scoring-gateway--high-availability-sla-track-3)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[System Architecture](#-master-system-architecture) • [Module Specifications](#-core-platform-modules--technical-specifications) • [Feature Matrix](#-enterprise-feature-matrix--verification-mapping) • [Directory Tree](#-complete-clean-architecture-directory-structure) • [API Blueprints](#-api-endpoint-blueprints--json-schemas) • [Quick Start](#-step-by-step-operator-quick-start)

</div>

---

## 💡 System Overview & Problem Statement

Financial institutions operate under strict regulatory constraints (**GDPR Art. 6/17**, **CCPA**, **Banking Secrecy Laws**) that prohibit pooling raw customer transaction records into central databases. This creates critical operational vulnerabilities:

- 💸 **Cross-Bank Velocity Fraud:** Organized syndicates transfer illicit funds sequentially across Bank Alpha -> Bank Beta -> Bank Gamma within minutes, clearing accounts before individual internal rules trigger.
- 🥷 **Structured Mule Networks (Smurfing):** Money laundering networks distribute structured micro-transactions across multiple institutions to remain below mandatory single-bank reporting thresholds.

The **Collaborative Fraud Intelligence Platform** solves this paradox. By combining **Federated Machine Learning (FL)**, **Differential Privacy ($\epsilon, \delta$)**, **Secure Aggregation (SecAgg)**, and **Byzantine-Robust Consensus**, member institutions train a global fraud detection model collaboratively—without ever exposing raw customer data or violating banking secrecy laws.

---

## 🏛️ Master System Architecture

### High-Level Topology ASCII Diagram

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

### End-to-End Federated Execution Flow

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

## ⚙️ Core Platform Modules & Technical Specifications

### 🧬 Privacy-Preserving Federated Learning (Track 1)

- **Local Training Pipelines:** Local PyTorch MLPs, Streaming Graph Neural Networks (GNN), and Federated XGBoost execute on isolated bank holdout splits.
- **Differential Privacy ($\epsilon, \delta$):** Adds Opacus Gaussian noise to $L_2$ norm clipped gradients:
  $$\sigma = \frac{\sqrt{2 \ln(1.25/\delta)}}{\epsilon}, \quad \bar{g}_i = \frac{g_i}{\max\left(1, \frac{\|g_i\|_2}{C}\right)}$$
  Enforces strict privacy bounds ($\epsilon \le 2.0$, $\delta \le 10^{-5}$) to prevent reconstruction attacks.
- **Secure Aggregation (SecAgg):** Applies pairwise cryptographic seed masking ($y_k = w_k + \sum_{j > k} s_{kj} - \sum_{j < k} s_{jk} \pmod{2^{32}}$) so individual updates remain hidden from the coordinator.
- **Byzantine-Robust Server Aggregation:** Supports `FedAvg`, `Krum`, `Multi-Krum`, `Trimmed Mean`, and `Coordinate Median` to resist up to 50% malicious poisoning updates.
- **Spectral Poisoning Defense (`spectral_defense.py`):** Uses top singular value decomposition (SVD) of the weight matrix to isolate and prune backdoor poisoners.
- **Canary Quality Gate:** Validates candidate models against global holdout sets ($\text{AUC}_{\text{candidate}} \ge \text{AUC}_{\text{active}} - \text{tolerance}$) before promotion.
- **Shadow Prediction Traffic Routing:** Directs 10% of live traffic to candidate models in shadow mode for real-time validation.
- **Automatic Rollback Manager (`auto_rollback.py`):** Automatically reverts to previous stable champion models if live metrics breach thresholds ($\text{AUC} < 0.65$, latency $> 200\text{ms}$, or $\text{FPR} > 5\%$).
- **PSI Drift-Triggered Retraining (`automated_retraining.py`):** Initiates a new federated training round automatically when Population Stability Index exceeds limit ($\text{PSI} \ge 0.20$).

---

### 🧠 Collaborative AML Intelligence & 9-Signal Risk Engine (Track 2)

- **9-Signal Composite Risk Scoring:** Evaluates 9 distinct anti-fraud signals into a unified risk score ($0 - 1000$):
  1. $S_{\text{local}}$: Local PyTorch model probability score.
  2. $S_{\text{velocity}}$: Cross-bank 1-hour transaction velocity anomaly.
  3. $S_{\text{graph}}$: Graph Neural Network entity centrality risk index.
  4. $S_{\text{typology}}$: Known money laundering typology pattern match score.
  5. $S_{\text{amount}}$: Statistical Z-score transaction amount deviation.
  6. $S_{\text{device}}$: Device fingerprinting & IP reputation risk index.
  7. $S_{\text{temporal}}$: Off-hours & rapid temporal clustering anomaly score.
  8. $S_{\text{mule}}$: Probabilistic money mule account score.
  9. $S_{\text{structuring}}$: Structuring / smurfing pattern detection index.
- **Composite Formula:** $\text{Risk Score} = \min\left(1000, \max\left(0, \sum_{i=1}^{9} w_i S_i \times 1000\right)\right)$.
- **FinCEN BSA SAR XML E-Filing (`regulatory_reporter.py`):** Automatically serializes Suspicious Activity Report (SAR) XML documents conforming to FinCEN BSA Electronic Filing schemas upon case escalation.
- **Cryptographic Event Hash Chaining:** Chains analyst actions using SHA-256 block hashes ($H_i = \text{SHA-256}(L_i \mathbin{\Vert} H_{i-1})$) for non-repudiation and judicial admissibility.
- **Web3 CBDC Smart Contract Settlement (`ConsortiumIncentiveSettlement.sol`):** Manages token payouts (`wCBDC`, `USDC`, `e-TRY`) based on Leave-One-Out (LOO) Shapley contribution values.
- **On-Chain Quarantine Locks:** Locks token payouts and revokes voting rights (`BLOCKED_QUARANTINE`) for malicious or low-quality data contributors.

---

### ⚡ Real-Time Scoring Gateway & High-Availability SLA (Track 3)

- **Real-Time Scoring API (`POST /v1/inference/score`):** Processes incoming scoring requests under a sub-100ms SLA ($p95$). Returns decisions: `ALLOW` (<300), `REVIEW` (300-699), or `BLOCK` (>=700).
- **Fast SHAP Feature Explainer (`realtime_explainer.py`):** Computes Shapley feature attributions in under 1ms for instant analyst interpretability.
- **High-Availability Inference Fallback (`inference_fallback.py`):** Executes heuristic decision fallbacks if model service latency exceeds 150ms.
- **Real-Time SLA Latency Monitor (`sla_monitor.py`):** Tracks $p50, p95, p99$ latency percentiles and triggers alerts upon SLA breaches.
- **SLA/SLO Contract Enforcement (`sla_contract_engine.py`):** Tracks 99.9% uptime SLA compliance and generates contractual `PenaltyReport` issuing percentage-based billing service credits if uptime drops below 99.9%.

---

### 🛠️ MLOps, Governance, Operations & Security Controls (Track 4)

- **Human-in-the-Loop Case Management (`case_workbench.py`):** Governs 6-stage case progression (`NEW` -> `ASSIGNED` -> `UNDER_INVESTIGATION` -> `ESCALATED` -> `RESOLVED_CONFIRMED_FRAUD` / `RESOLVED_FALSE_POSITIVE`).

```mermaid
stateDiagram-v2
    [*] --> NEW
    NEW --> ASSIGNED: Assign Investigator
    ASSIGNED --> UNDER_INVESTIGATION: Start Analysis
    UNDER_INVESTIGATION --> ESCALATED: Escalate to Supervisor
    ESCALATED --> RESOLVED_CONFIRMED_FRAUD: Supervisor Signature (SIG_SUPERVISOR_*)
    ESCALATED --> RESOLVED_FALSE_POSITIVE: Supervisor Signature (SIG_SUPERVISOR_*)
    RESOLVED_CONFIRMED_FRAUD --> [*]
    RESOLVED_FALSE_POSITIVE --> [*]
```

> [!IMPORTANT]
> **Four-Eyes Supervisor Dual Sign-Off:** Case resolution strictly requires a cryptographic supervisor authorization starting with `SIG_SUPERVISOR_*`. Requisitions missing this signature are rejected with HTTP `403 Forbidden`.

- **Privacy-Preserving Label Feedback Loop (`label_privacy_guard.py`):** Validates incoming labels, enforcing zero-PII leak constraints and computing DP noise-protected local gradient updates ($\epsilon \le 2.0$).
- **Enterprise Data Retention & GDPR Art. 17 Engine (`retention_engine.py`):** Manages per-tenant TTL policies and executes cryptographic zeroization for customer identifiers, outputting an immutable `ErasureAuditRecord`.
- **Active-Passive Multi-Region Coordinator Failover (`region_failover.py`):** Monitors coordinator health, executing automated failover ($RTO < 30\text{s}$, $RPO = 0$) upon primary heartbeat failure (>15s).
- **Backup Integrity Verifier & Sandbox Restore Probes (`backup_verifier.py`):** Validates SHA-256 checksums and executes automated sandbox restore dry-runs (`run_sandbox_restore_probe`).
- **Developer Webhook Gateway (`webhook_service.py`):** Registers webhook subscriptions (`POST /v1/webhooks/subscriptions`) and signs outbound payloads with HMAC-SHA256 headers (`X-CFI-Signature`).
- **SRE Incident Triage Engine (`incident_triage.py`):** Automatically classifies system alerts into severity levels (`SEV1` to `SEV4`) and attaches step-by-step SRE remediation commands (`PlaybookAction`).
- **Zero-Downtime Platform Upgrade Manager (`zero_downtime_deployer.py`):** Orchestrates 5-stage rolling releases (`DRAINING_CONNECTIONS` -> `ROLLING_UPGRADE` -> `DUAL_VERSION_ACTIVE` -> `UPGRADE_COMPLETED`) with a 48-hour dual-version window (`UpgradeWindow`).
- **Commercial Multi-Role Web Management Console (`admin_console.py`):** Serves 4 distinct enterprise personas (`EXECUTIVE`, `COMPLIANCE_OFFICER`, `ML_ENGINEER`, `FRAUD_INVESTIGATOR`).
- **Official PyPI Operator CLI Utility (`cfi_cli.py`):** Provides terminal subcommands (`cfi-cli status`, `cfi-cli health`, `cfi-cli export-diagnostics`, `cfi-cli deploy`).
- **Edge Security Perimeter WAF Guard (`perimeter_waf.py`):** Filters malicious SQLi, XSS, and enforces strict IP whitelisting at the edge.
- **Air-Gapped Installer Package Builder (`airgap_installer.py`):** Packages self-contained, zero-internet tarball bundles validated with SHA-256 manifests.
- **Enterprise Security Attestations Auditor (`security_compliance.py`):** Audits platform controls against SOC2 Type II, ISO 27001, and GDPR Art. 17 standards.
- **Responsible Vulnerability Disclosure Policy:** Published in [SECURITY.md](file:///c:/Users/Yusuf/Desktop/projects/Privacy-preserving%20cross-bank%20fraud%20detection%20using%20Federated%20Learning/SECURITY.md).
- **SIEM Log Exporter (`siem_exporter.py`):** Exports audit events in Syslog Common Event Format (CEF `CEF:0|CFI|...`), Splunk HEC, and Datadog JSON formats.
- **Support Diagnostic Compiler (`support_diagnostics.py`):** Packages PII-redacted (emails, IBANs), SHA-256 signed telemetry bundles for customer support.

---

## 📊 Enterprise Feature Matrix & Verification Mapping

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

## 🛡️ Threat Modeling Summary (STRIDE Matrix)

| STRIDE Category | Identified Threat | Mitigating Architectural Safeguard | Verification File |
| :--- | :--- | :--- | :--- |
| **Spoofing** | Node impersonation during FL aggregation | mTLS x509 Mutual Auth & HMAC-SHA256 signatures | `webhook_service.py` |
| **Tampering** | Model gradient poisoning or weight corruption | Byzantine-robust Krum / Median & SecAgg | `test_disaster_recovery_failover.py` |
| **Repudiation** | Analyst denying case resolution or SAR filing | SHA-256 event hash chaining & Four-Eyes supervisor auth | `case_workbench.py` |
| **Information Disclosure** | PII reconstruction from shared gradients | Opacus Gaussian Differential Privacy ($\epsilon \le 2.0$) | `label_privacy_guard.py` |
| **Denial of Service** | Scoring API flooding during peak traffic | Token Bucket rate-limiting & Edge WAF Guard | `perimeter_waf.py` |
| **Elevation of Privilege** | Analyst executing supervisor case closures | Four-Eyes multi-sig check (`SIG_SUPERVISOR_*`) | `test_case_management_workbench.py` |

---

## 📋 Regulatory Compliance Alignment Matrix

| Framework / Regulation | Mandatory Requirement | Platform Implementation |
| :--- | :--- | :--- |
| **GDPR Article 6 & 17** | Lawful processing and Right-to-be-Forgotten zeroization | `retention_engine.py` executes cryptographic zeroization. |
| **EU AI Act (High-Risk AI)** | Model interpretability, bias evaluation & audit trail | `ai_act_compliance.py` & `realtime_explainer.py`. |
| **SR 11-7 Model Risk Governance** | Model validation, champion/challenger, and drift monitoring | `model_governance.py` & `automated_retraining.py`. |
| **FinCEN BSA Regulations** | Suspicious Activity Reporting (SAR) e-filing XML compliance | `regulatory_reporter.py` serializes BSA SAR XML. |
| **SOC2 Type II & ISO 27001** | Security perimeter, access control, and incident triage | `security_compliance.py` audits 5 core controls. |

---

## 📁 Complete Clean Architecture Directory Structure

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

## 📡 API Endpoint Blueprints & JSON Schemas

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

## 💻 CLI Tooling Usage Guide (`cfi-cli`)

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

## ⚙️ Platform Configuration Reference

| Variable Name | Default Value | Description |
| :--- | :--- | :--- |
| `CFI_ENV` | `production` | Environment mode (`development`, `staging`, `production`). |
| `CFI_DP_EPSILON` | `2.0` | Differential Privacy maximum epsilon budget ($\epsilon$). |
| `CFI_DP_DELTA` | `1e-5` | Differential Privacy delta failure probability ($\delta$). |
| `CFI_INFERENCE_SLA_MS` | `100.0` | Maximum acceptable latency for scoring inference ($p95$). |
| `CFI_DISASTER_RECOVERY_ROLE` | `PRIMARY` | Region DR role (`PRIMARY` or `STANDBY`). |
| `CFI_SECAgg_ENABLED` | `true` | Enables pairwise cryptographic seed masking. |

---

## 🚀 Step-by-Step Operator Quick Start

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

## 🧪 Verification and Quality Testing Suite

Execute full automated unit test suite:

```bash
pytest backend/tests/unit/ -v
```

Execute static code format and lint validation:

```bash
ruff check backend/app/ backend/tests/
```

---

## 📄 License & Academic Citation

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
