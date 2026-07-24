# ⚡ Real-Time Fraud Risk Inference API Specification

The Real-Time Fraud Scoring Gateway provides online transaction authorization for core banking & payment switch integrations with sub-100ms response times ($p95$).

---

## 📌 Endpoint Overview

- **Endpoint**: `POST /v1/inference/score`
- **Content-Type**: `application/json`
- **SLA**: $<100\text{ms}$ ($p95$) latency guarantee backed by automatic heuristic fallback.

---

## 📥 Request Body Schema

```json
{
  "transaction_id": "tx_88992211",
  "amount": 1250.50,
  "currency": "USD",
  "source_account": "acc_src_991",
  "target_account": "acc_dst_002",
  "merchant_category": "crypto_exchange",
  "velocity_1h": 3,
  "force_fallback": false
}
```

---

## 📤 Response Schema

```json
{
  "transaction_id": "tx_88992211",
  "risk_score": 0.40,
  "decision": "REVIEW",
  "latency_ms": 4.12,
  "evaluated_by": "ML_MODEL",
  "explanation": "ML Model: High-risk merchant"
}
```

---

## ⚖️ Decision Categorization Rules

| Decision | Risk Score Range | Action Executed |
| :--- | :--- | :--- |
| **`ALLOW`** | $0.00 \le \text{Score} < 0.35$ | Transaction authorized immediately. |
| **`REVIEW`** | $0.35 \le \text{Score} < 0.70$ | Transaction held for analyst investigation. |
| **`BLOCK`** | $0.70 \le \text{Score} \le 1.00$ | Transaction rejected immediately. |

---

## 🛡️ Heuristic Fallback SLA Guarantee

If primary PyTorch ML model execution fails or exceeds timeout thresholds, the system triggers `InferenceFallbackEngine` to evaluate velocity, amount, and merchant category heuristics without blocking payment flows (`evaluated_by: "HEURISTIC_FALLBACK"`).
