# 🗑️ Enterprise Data Retention & GDPR Article 17 Erasure Specification

The Automated Retention & Erasure Engine enforces Time-To-Live (TTL) data purging and fulfills GDPR Article 17 Right-to-be-Forgotten requests with cryptographic zeroization and tamper-proof audit trails.

---

## 📌 Data Retention Categories & Default TTLs

| Data Category | Default TTL | Erasure Method | Description |
| :--- | :--- | :--- | :--- |
| **`TRANSACTION_LOGS`** | 90 Days | `CRYPTOGRAPHIC_ZEROIZATION` | Raw transaction telemetry logs. |
| **`INFERENCE_AUDITS`** | 180 Days | `ANONYMIZATION` | Real-time inference scoring audit logs. |
| **`GRAPH_EDGES`** | 30 Days | `HARD_DELETE` | Temporary graph relationship edges. |
| **`EXPLAINABILITY_REPORTS`** | 60 Days | `CRYPTOGRAPHIC_ZEROIZATION` | SHAP feature attribution reports. |

---

## ⚖️ GDPR Article 17 Right-to-be-Forgotten Protocol

When a customer submits a erasure request under GDPR Article 17:
1. `execute_gdpr_right_to_be_forgotten` is invoked with the HMAC-SHA256 hashed entity identifier (`entity_id_hash`).
2. All linked tenant records cross transaction tables, feature stores, and relationship graphs are zeroized.
3. A SHA-256 signed `ErasureAuditRecord` is generated and committed to the immutable compliance ledger.
