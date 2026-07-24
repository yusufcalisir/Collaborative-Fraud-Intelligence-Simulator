# Collaborative Fraud Intelligence Platform

A production-grade, enterprise-ready platform delivering privacy-preserving, cross-institution financial fraud detection and Collaborative Anti-Money Laundering (AML) intelligence. This platform empowers financial institutions to train federated machine learning models and share real-time risk indicators without exposing customer Personally Identifiable Information (PII) or violating global privacy regulations such as GDPR, CCPA, and banking secrecy laws.

[![CI](https://github.com/yusufcalisir/Collaborative-Fraud-Intelligence-Simulator/actions/workflows/ci.yml/badge.svg)](https://github.com/yusufcalisir/Collaborative-Fraud-Intelligence-Simulator/actions)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688.svg)](https://fastapi.tiangolo.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.2.0-EE4C2C.svg)](https://pytorch.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

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

---

> [!NOTE]
> **Enterprise Objective:** This platform resolves the tension between stringent data privacy compliance and cross-bank fraud intelligence. By utilizing distributed Federated Learning (FL), Differential Privacy ($\epsilon, \delta$), and cryptographic risk sharing, financial consortiums collaborate in real time to stop multi-institution fraud syndicates without centralizing or decrypting raw transaction records.

---

## Table of Contents

- [The Core Challenge: Siloed Fraud Detection](#the-core-challenge-siloed-fraud-detection)
- [Enterprise Architecture Overview](#enterprise-architecture-overview)
- [Track 1: Privacy-Preserving Federated Learning & Differential Privacy](#track-1-privacy-preserving-federated-learning--differential-privacy)
- [Track 2: Collaborative AML Intelligence & 9-Signal Risk Engine](#track-2-collaborative-aml-intelligence--9-signal-risk-engine)
- [Track 3: Microservices, Gateway & High-Availability SLA](#track-3-microservices-gateway--high-availability-sla)
- [Track 4: MLOps, Governance, Security & Operations](#track-4-mlops-governance-security--operations)
  - [⚡ Real-Time Fraud Risk Scoring Engine & Sub-100ms SLA](#-real-time-fraud-risk-scoring-engine--sub-100ms-sla)
  - [🕵️ Human-in-the-Loop Case Management & Workbench](#-human-in-the-loop-case-management--workbench)
  - [🔒 Privacy-Preserving Label Feedback Loop & DP Noise Guard](#-privacy-preserving-label-feedback-loop--dp-noise-guard)
  - [🗑️ Enterprise Data Retention & GDPR Article 17 Erasure Engine](#%EF%B8%8F-enterprise-data-retention--gdpr-article-17-erasure-engine)
  - [🌍 Active-Passive Multi-Region Coordinator Failover](#-active-passive-multi-region-coordinator-failover)
  - [🛡️ Automated Backup Verification & Sandbox Restore Probes](#%EF%B8%8F-automated-backup-verification--sandbox-restore-probes)
  - [🔌 Public Integration API & Webhook Gateway](#-public-integration-api--webhook-gateway)
  - [📊 Enterprise SLA/SLO Monitoring & Contract Enforcement](#-enterprise-slaslo-monitoring--contract-enforcement)
  - [🚨 SRE Operational Runbooks & Incident Playbooks](#-sre-operational-runbooks--incident-playbooks)
  - [🔄 Zero-Downtime Platform Upgrades & Client Compatibility](#-zero-downtime-platform-upgrades--client-compatibility)
  - [🎛️ Commercial Multi-Role Web Management Console](#%EF%B8%8F-commercial-multi-role-web-management-console)
  - [💻 Official CLI Tooling (`cfi-cli`)](#-official-cli-tooling-cfi-cli)
  - [🛡️ Edge Security Perimeter & Air-Gapped Deployment Bundle](#%EF%B8%8F-edge-security-perimeter--air-gapped-deployment-bundle)
  - [📑 Enterprise Security Attestations & Compliance Matrix](#-enterprise-security-attestations--compliance-matrix)
  - [📊 SIEM Log Forwarding & Automated Support Telemetry](#-siem-log-forwarding--automated-support-telemetry)
  - [🪙 Web3 & CBDC Smart Contract Incentive Settlement](#-web3--cbdc-smart-contract-incentive-settlement)
- [Feature Matrix & Enterprise Compliance](#feature-matrix--enterprise-compliance)
- [Threat Modeling Summary (STRIDE Matrix)](#threat-modeling-summary-stride-matrix)
- [Complete Clean Architecture Directory Structure](#complete-clean-architecture-directory-structure)
- [API Endpoint Blueprints & JSON Schemas](#api-endpoint-blueprints--json-schemas)
- [Quick Start & Operator Guide](#quick-start--operator-guide)
- [Automated Verification and Quality Suite](#automated-verification-and-quality-suite)
- [License](#license)

---

## The Core Challenge: Siloed Fraud Detection

Financial institutions historically detect fraud and money laundering in absolute isolation. Each bank trains machine learning models solely on internal transaction data, creating critical vulnerabilities:

1. **Cross-Bank Velocity Fraud:** Fraudsters exploit the blind spots between institutions, rapidly transferring stolen funds across Bank A, Bank B, and Bank C before any single bank detects the pattern.
2. **Structured Syndicate Networks:** Mule account rings distribute structured transactions across several institutions to remain below single-bank detection thresholds.
3. **Privacy & Regulatory Barriers:** Strict privacy laws (GDPR Art. 6/17, CCPA, Banking Secrecy Act) prohibit banks from pooling raw customer transaction records into a centralized database.

---

## Enterprise Architecture Overview

The platform uses a decoupled clean architecture consisting of four core tracks:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                   Collaborative Fraud Intelligence Core                  │
├───────────────────┬───────────────────┬───────────────────┬──────────────┤
│      Track 1      │      Track 2      │      Track 3      │   Track 4    │
│    Federated      │   9-Signal Risk   │   Microservices & │    MLOps &   │
│     Learning      │   Engine & AML    │   API Gateway     │  Governance  │
└───────────────────┴───────────────────┴───────────────────┴──────────────┘
```

---

## Track 1: Privacy-Preserving Federated Learning & Differential Privacy

### 1.1 Local Model Training & Private Datasets
Each participating bank node (Bank Alpha, Bank Beta, Bank Gamma) trains local PyTorch models on isolated transaction stores. Raw financial records never leave the institution's security perimeter.

### 1.2 Differential Privacy ($\epsilon, \delta$)
Integrates Opacus Gaussian noise addition and L2 gradient clipping to mathematically bound privacy leakage.
$$\sigma = \frac{\sqrt{2 \ln(1.25/\delta)}}{\epsilon}$$
The noise scale $\sigma$ guarantees differential privacy, preventing reconstruction attacks or gradient inversion attempts by untrusted participants.

### 1.3 Secure Aggregation (SecAgg) & Outbound Outlier Guard
Pairwise cryptographic masking hides individual model updates before transmission:
$$w_{k} + \sum_{j > k} s_{kj} - \sum_{j < k} s_{jk} \pmod{2^{32}}$$
The outbound outlier guard flags anomalous weight distributions before inclusion in global model updates.

### 1.4 Byzantine-Robust Aggregation Algorithms
The central coordinator supports multiple aggregation algorithms to resist adversarial poisoning attacks:
- **FedAvg**: Standard weighted average based on local dataset sizes.
- **Krum & Multi-Krum**: Selects updates closest to their $n - f - 2$ nearest neighbors.
- **Trimmed Mean & Coordinate Median**: Computes coordinate-wise trimmed statistics to eliminate extreme malicious outliers.

### 1.5 Canary Evaluation Quality Gate & Performance Rollback
- **Canary Gate**: A newly aggregated candidate model is benchmarked against a global holdout set. It is only promoted if $\text{AUC}_{\text{candidate}} \ge \text{AUC}_{\text{active}} - \text{tolerance}$.
- **Shadow Inference**: Routes 10% of live prediction traffic to candidate models in shadow mode for evaluation.
- **Automatic Rollback**: Instantly demotes champion models if live performance degrades ($\text{AUC} < 0.65$, latency $> 200\text{ms}$, or $\text{FPR} > 5\%$).
- **PSI Drift-Triggered Retraining**: Automatically triggers a new federated training round when Population Stability Index ($\text{PSI} \ge 0.20$) indicates distribution drift.

---

## Track 2: Collaborative AML Intelligence & 9-Signal Risk Engine

### 2.1 9-Signal Composite Risk Scoring Formula
Combines local model outputs, cross-bank velocity metrics, and entity graph topologies into a unified risk score ($0 - 1000$):
$$\text{Risk Score} = w_1 S_{\text{local}} + w_2 S_{\text{velocity}} + w_3 S_{\text{graph}} + \dots + w_9 S_{\text{typology}}$$

### 2.2 FinCEN BSA Suspicious Activity Report (SAR) XML E-Filing
Automatically serializes Suspicious Activity Report (SAR) XML files conforming to FinCEN BSA e-filing schemas when a case is escalated to `RESOLVED_CONFIRMED_FRAUD`.

### 2.3 Cryptographic Event Hash Chaining
Analyst actions and timeline entries are chained using SHA-256 block hashing:
$$H_i = \text{SHA-256}(L_i \mathbin{\Vert} H_{i-1})$$
This establishes an immutable audit trail suitable for judicial admissibility.

### 2.4 Evidence Registry & Hashing
Compiles KYC profiles, transaction logs, and ledger proofs validated with SHA-256 content hashes to establish chain-of-custody.

---

## Track 3: Microservices, Gateway & High-Availability SLA

### 3.1 FastAPI & Async Architecture
Delivers high-throughput REST and gRPC endpoints for real-time inference, case management, and system administration.

### 3.2 Token Bucket Rate Limiting
Enforces per-tenant rate limits to protect system resources during high-traffic spikes.

### 3.3 Prometheus & Grafana Monitoring
Exports real-time metrics tracking latency, throughput, error rates, and system resource utilization.

---

## Track 4: MLOps, Governance, Security & Operations

### ⚡ Real-Time Fraud Risk Scoring Engine & Sub-100ms SLA
- **Inference Gateway Router**: `POST /v1/inference/score` scores incoming transactions in real time, returning `ALLOW`, `REVIEW`, or `BLOCK` decisions within a sub-100ms SLA.
- **Sub-Millisecond Feature Attributions**: `FastInferenceExplainer` computes real-time Shapley feature contributions in under 1ms.
- **Inference Fallback Engine**: `InferenceFallbackEngine` provides high-availability heuristic fallback decisions if model latency exceeds 150ms.
- **SLA Monitor**: `RealtimeSLAMonitor` tracks $p50, p95, p99$ latency percentiles and triggers alerts upon SLA breaches.
- **Documentation**: [docs/realtime_inference_api.md](file:///c:/Users/Yusuf/Desktop/projects/Privacy-preserving%20cross-bank%20fraud%20detection%20using%20Federated%20Learning/docs/realtime_inference_api.md)

### 🕵️ Human-in-the-Loop Case Management & Workbench
- **6-Stage Case State Machine**: `CaseLifecycleStateMachine` governs case progression (`NEW` -> `ASSIGNED` -> `UNDER_INVESTIGATION` -> `ESCALATED` -> `RESOLVED_CONFIRMED_FRAUD` / `RESOLVED_FALSE_POSITIVE`).
- **Four-Eyes Supervisor Dual-Authorization**: Enforces mandatory supervisor cryptographic sign-off (`SIG_SUPERVISOR_*`) before any case can be resolved.
- **Documentation**: [docs/case_management_spec.md](file:///c:/Users/Yusuf/Desktop/projects/Privacy-preserving%20cross-bank%20fraud%20detection%20using%20Federated%20Learning/docs/case_management_spec.md)

### 🔒 Privacy-Preserving Label Feedback Loop & DP Noise Guard
- **Label Privacy Guard**: `LabelPrivacyGuard` validates incoming label feedback, enforcing zero-PII leak constraints (HMAC-SHA256 checks and raw PII blocking).
- **Federated Gradient Update**: `LocalLabelFeedbackPipeline` computes Gaussian Differential Privacy noise-protected local gradient deltas ($\epsilon \le 2.0$).
- **Documentation**: [docs/label_feedback_loop_spec.md](file:///c:/Users/Yusuf/Desktop/projects/Privacy-preserving%20cross-bank%20fraud%20detection%20using%20Federated%20Learning/docs/label_feedback_loop_spec.md)

### 🗑️ Enterprise Data Retention & GDPR Article 17 Erasure Engine
- **Automated Retention Engine**: `AutomatedRetentionEngine` configures per-tenant Time-To-Live (TTL) policies and purges expired records across data categories.
- **GDPR Article 17 Right-to-be-Forgotten**: Executes cryptographic zeroization for requested customer identifiers and outputs an immutable `ErasureAuditRecord`.
- **Documentation**: [docs/data_retention_policy_spec.md](file:///c:/Users/Yusuf/Desktop/projects/Privacy-preserving%20cross-bank%20fraud%20detection%20using%20Federated%20Learning/docs/data_retention_policy_spec.md)

### 🌍 Active-Passive Multi-Region Coordinator Failover
- **Multi-Region Failover Manager**: `MultiRegionFailoverManager` monitors active primary and passive standby coordinator nodes, executing automated failover ($RTO < 30s$, $RPO = 0$) upon primary heartbeat failure (>15s).
- **Documentation**: [docs/disaster_recovery_plan.md](file:///c:/Users/Yusuf/Desktop/projects/Privacy-preserving%20cross-bank%20fraud%20detection%20using%20Federated%20Learning/docs/disaster_recovery_plan.md)

### 🛡️ Automated Backup Verification & Sandbox Restore Probes
- **Backup Integrity Verifier**: `BackupVerifier` validates SHA-256 checksums and executes automated sandbox restore dry-runs (`run_sandbox_restore_probe`).
- **Corruption Detection**: Instantly flags tampered or degraded backup artifacts as `CORRUPTED` and alerts compliance operators.
- **Documentation**: [docs/backup_verification_spec.md](file:///c:/Users/Yusuf/Desktop/projects/Privacy-preserving%20cross-bank%20fraud%20detection%20using%20Federated%20Learning/docs/backup_verification_spec.md)

### 🔌 Public Integration API & Webhook Gateway
- **Webhook Gateway Router**: `POST /v1/webhooks/subscriptions` registers developer webhook endpoints for event notifications (`ALERT_CREATED`, `CASE_RESOLVED`, `MODEL_PROMOTED`, `DRIFT_DETECTED`).
- **HMAC-SHA256 Payload Signing**: All webhook deliveries compute and append a cryptographic `X-CFI-Signature` header (`HMAC_SHA256(secret_key, payload_body)`).
- **Documentation**: [docs/public_api_webhooks_spec.md](file:///c:/Users/Yusuf/Desktop/projects/Privacy-preserving%20cross-bank%20fraud%20detection%20using%20Federated%20Learning/docs/public_api_webhooks_spec.md)

### 📊 Enterprise SLA/SLO Monitoring & Contract Enforcement
- **Contract Engine**: `SLAContractEngine` tracks error budget burn rates (99.9% uptime SLA, <100ms $p95$ latency SLO).
- **Automated Service Credits**: Automatically calculates contractual billing credit discounts (`PenaltyReport`) if measured monthly availability drops below 99.9%.
- **Documentation**: [docs/sla_slo_contract_spec.md](file:///c:/Users/Yusuf/Desktop/projects/Privacy-preserving%20cross-bank%20fraud%20detection%20using%20Federated%20Learning/docs/sla_slo_contract_spec.md)

### 🚨 SRE Operational Runbooks & Incident Playbooks
- **Incident Triage Engine**: `IncidentTriageEngine` automatically classifies system alerts (`PRIVACY_LEAK_ALERT`, `CONSENSUS_FAILURE`, `SLA_BREACH`, `PSI_DRIFT_SPIKE`) into severity levels (`SEV1` to `SEV4`).
- **Mitigation Playbooks**: Attaches step-by-step SRE remediation commands (`PlaybookAction`) for emergency node isolation, DR failover, and retraining.
- **Documentation**: [docs/incident_response_playbook.md](file:///c:/Users/Yusuf/Desktop/projects/Privacy-preserving%20cross-bank%20fraud%20detection%20using%20Federated%20Learning/docs/incident_response_playbook.md)

### 🔄 Zero-Downtime Platform Upgrades & Client Compatibility
- **Deployment Manager**: `ZeroDowntimeDeploymentManager` orchestrates 5-stage rolling releases (`DRAINING_CONNECTIONS` -> `ROLLING_UPGRADE` -> `DUAL_VERSION_ACTIVE` -> `UPGRADE_COMPLETED`).
- **Connection Draining & Compatibility**: Gracefully drains active client connections without dropping requests while providing a 48-hour dual-version compatibility window (`UpgradeWindow`).
- **Documentation**: [docs/zero_downtime_upgrade_strategy.md](file:///c:/Users/Yusuf/Desktop/projects/Privacy-preserving%20cross-bank%20fraud%20detection%20using%20Federated%20Learning/docs/zero_downtime_upgrade_strategy.md)

### 🎛️ Commercial Multi-Role Web Management Console
- **Tailored Personas**: Serves 4 distinct enterprise personas (`EXECUTIVE`, `COMPLIANCE_OFFICER`, `ML_ENGINEER`, `FRAUD_INVESTIGATOR`) via `GET /v1/admin/dashboard/role-config`.
- **Unified Summary Metrics**: `GET /v1/admin/dashboard/summary` streams real-time active node counts, global model AUC, open case statistics, and SLA compliance.
- **Documentation**: [docs/commercial_console_ui_spec.md](file:///c:/Users/Yusuf/Desktop/projects/Privacy-preserving%20cross-bank%20fraud%20detection%20using%20Federated%20Learning/docs/commercial_console_ui_spec.md)

### 💻 Official CLI Tooling (`cfi-cli`)
- **Standardized Operator Commands**: Provides terminal subcommands (`cfi-cli status`, `cfi-cli health`, `cfi-cli export-diagnostics`, `cfi-cli deploy`).
- **Packaging & Console Script**: PyPI console entrypoint configured in `pyproject.toml` (`app.presentation.cli.cfi_cli:main`).
- **Documentation**: [docs/cfi_cli_user_guide.md](file:///c:/Users/Yusuf/Desktop/projects/Privacy-preserving%20cross-bank%20fraud%20detection%20using%20Federated%20Learning/docs/cfi_cli_user_guide.md)

### 🛡️ Edge Security Perimeter & Air-Gapped Deployment Bundle
- **Perimeter WAF Guard**: `PerimeterWAFGuard` filters malicious SQLi, XSS, and enforces strict IP whitelisting at the edge.
- **Air-Gapped Installer Builder**: `AirGapBundleBuilder` packages self-contained, zero-internet tarball bundles validated with SHA-256 manifests.
- **Documentation**: [docs/airgapped_deployment_guide.md](file:///c:/Users/Yusuf/Desktop/projects/Privacy-preserving%20cross-bank%20fraud%20detection%20using%20Federated%20Learning/docs/airgapped_deployment_guide.md)

### 📑 Enterprise Security Attestations & Compliance Matrix
- **Compliance Auditor Engine**: `SecurityComplianceEngine` audits platform controls against SOC2 Type II, ISO 27001, and GDPR Art. 17 standards.
- **Responsible Vulnerability Disclosure**: Policy and PGP key details published in [SECURITY.md](file:///c:/Users/Yusuf/Desktop/projects/Privacy-preserving%20cross-bank%20fraud%20detection%20using%20Federated%20Learning/SECURITY.md).
- **Documentation**: [docs/security_controls_matrix.md](file:///c:/Users/Yusuf/Desktop/projects/Privacy-preserving%20cross-bank%20fraud%20detection%20using%20Federated%20Learning/docs/security_controls_matrix.md)

### 📊 SIEM Log Forwarding & Automated Support Telemetry
- **SIEM CEF Exporter**: `SIEMLogExporter` exports audit events in Syslog Common Event Format (CEF), Splunk HEC, and Datadog JSON formats.
- **Support Diagnostic Compiler**: `SupportDiagnosticCompiler` packages PII-redacted, SHA-256 signed telemetry bundles for customer support.
- **Documentation**: [docs/siem_and_support_guide.md](file:///c:/Users/Yusuf/Desktop/projects/Privacy-preserving%20cross-bank%20fraud%20detection%20using%20Federated%20Learning/docs/siem_and_support_guide.md)

### 🪙 Web3 & CBDC Smart Contract Incentive Settlement
- **EVM Smart Contract**: `ConsortiumIncentiveSettlement.sol` executes token disbursements (`wCBDC`, `USDC`, `e-TRY`) based on Leave-One-Out (LOO) Shapley contributions.
- **Free-Rider Quarantine**: Executes on-chain quarantine locks (`BLOCKED_QUARANTINE`) for malicious or low-quality data contributors.

---

## Feature Matrix & Enterprise Compliance

| Feature / Module | Specification | Enterprise Standard | Verification Engine | Status |
| :--- | :--- | :--- | :--- | :--- |
| **Real-Time Scoring API** | Sub-100ms Latency SLA | Banking Core API | `realtime_inference.py` | `PASS` |
| **SHAP Feature Explainer** | Sub-ms Feature Contributions | SR 11-7 / Model Governance | `realtime_explainer.py` | `PASS` |
| **Case Management Workbench** | 6-Stage Lifecycle + 4-Eyes Auth | AML Investigation Standards | `case_workbench.py` | `PASS` |
| **Differential Privacy Guard** | Gaussian Noise ($\epsilon \le 2.0$) | GDPR / CCPA Compliance | `label_privacy_guard.py` | `PASS` |
| **GDPR Data Retention** | Automated TTL & Right-to-be-Forgotten | GDPR Article 17 | `retention_engine.py` | `PASS` |
| **Multi-Region Coordinator Failover** | Active-Passive ($RTO < 30s$) | Business Continuity | `region_failover.py` | `PASS` |
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

## Threat Modeling Summary (STRIDE Matrix)

| STRIDE Category | Identified Threat | Mitigating Architectural Safeguard | Verification |
| :--- | :--- | :--- | :--- |
| **Spoofing** | Impersonation of a bank node during aggregation | mTLS x509 Mutual Authentication & HMAC-SHA256 signatures | `webhook_service.py` |
| **Tampering** | Model weight poisoning or dataset corruption | Byzantine-robust Krum / Coordinate Median & SecAgg | `test_disaster_recovery_failover.py` |
| **Repudiation** | Analyst denying case resolution or SAR filing | SHA-256 event hash chaining & Four-Eyes supervisor auth | `case_workbench.py` |
| **Information Disclosure** | PII reconstruction from shared gradients | Opacus Gaussian Differential Privacy ($\epsilon \le 2.0$) | `label_privacy_guard.py` |
| **Denial of Service** | API flooding during peak fraud incidents | Token Bucket rate-limiting & Edge WAF Guard | `perimeter_waf.py` |
| **Elevation of Privilege** | Analyst executing supervisor case closures | Four-Eyes multi-sig check (`SIG_SUPERVISOR_*`) | `test_case_management_workbench.py` |

---

## Complete Clean Architecture Directory Structure

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

## API Endpoint Blueprints & JSON Schemas

### Real-Time Inference Scoring Endpoint

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

### Developer Webhook Registration Endpoint

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

---

## Quick Start & Operator Guide

### 1. Prerequisites

- Python 3.12+
- PyTorch 2.2+
- FastAPI & Uvicorn

### 2. Environment Setup

```bash
# Clone the repository
git clone https://github.com/yusufcalisir/Collaborative-Fraud-Intelligence-Simulator.git
cd Collaborative-Fraud-Intelligence-Simulator

# Install backend package and cfi-cli
cd backend
pip install -e .
```

### 3. Running `cfi-cli`

```bash
# Check platform status
cfi-cli status

# Run system health checks
cfi-cli health

# Export diagnostic telemetry bundle
cfi-cli export-diagnostics --output /tmp/cfi_diag.json
```

---

## Automated Verification and Quality Suite

Run the full automated unit test suite:

```bash
pytest backend/tests/unit/ -v
```

Run static code format and lint checks:

```bash
ruff check backend/app/ backend/tests/
```

---

## License

Distributed under the MIT License. See `LICENSE` for details.
