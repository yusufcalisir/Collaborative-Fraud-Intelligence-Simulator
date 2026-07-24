# 🔌 Public Integration API & Developer Webhooks Specification

The Webhook Gateway allows financial institutions and developer partners to subscribe to real-time notification events (`ALERT_CREATED`, `CASE_RESOLVED`, `MODEL_PROMOTED`, `DRIFT_DETECTED`) delivered with HMAC-SHA256 signature verification.

---

## 📌 Endpoint Overview

- **Subscription Endpoint**: `POST /v1/webhooks/subscriptions`
- **Test Dispatch Endpoint**: `POST /v1/webhooks/test-dispatch`

---

## 🔐 HMAC-SHA256 Signature Verification

Every outgoing HTTP POST request from the Webhook Gateway includes an `X-CFI-Signature` header:

```http
POST /webhooks/cfi HTTP/1.1
Host: api.bank-alpha.com
X-CFI-Signature: sha256=a8f5f167f44f4964e6c998dee827110c...
Content-Type: application/json

{
  "event_id": "evt_99882211",
  "event_type": "ALERT_CREATED",
  "payload": { ... }
}
```

### Verification Logic (Python Example)

```python
import hmac, hashlib

def verify_webhook(secret_key: str, payload_bytes: bytes, received_sig: str) -> bool:
    expected_sig = "sha256=" + hmac.new(
        secret_key.encode("utf-8"),
        payload_bytes,
        digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_sig, received_sig)
```
