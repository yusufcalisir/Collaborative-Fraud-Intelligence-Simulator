# 🔌 Enterprise Bank Connector SDK Integration Guide (`cfi-connector-sdk`)

The `cfi-connector-sdk` package provides standardized, versioned interfaces for external banking IT engineering teams to seamlessly connect core banking systems (Flexcube, Temenos, Thought Machine, Finacle) to the Collaborative Fraud Intelligence (CFI) network.

---

## 🛠️ Installation

Install the SDK directly from repository root or wheel distribution:

```bash
pip install sdk/python
```

---

## 🧩 Implementing Custom Adapters

### 1. Custom Transaction Adapter

Extend `BaseTransactionAdapter` to transform native core banking JSON or XML records into standardized `NormalizedTransaction` objects:

```python
from typing import Any, Dict
from cfi_connector_sdk import BaseTransactionAdapter, NormalizedTransaction

class CoreBankingTransactionAdapter(BaseTransactionAdapter):
    def parse_native_payload(self, payload: Dict[str, Any]) -> NormalizedTransaction:
        return NormalizedTransaction(
            transaction_id=payload["tx_ref_num"],
            account_id=payload["debtor_iban"],
            counterparty_account_id=payload["creditor_iban"],
            amount=float(payload["monetary_amount"]),
            currency=payload.get("currency_code", "USD"),
            merchant_category_code=payload.get("mcc", "0000"),
            channel_type=payload.get("payment_channel", "ONLINE"),
        )
```

---

### 2. Privacy-Preserving Customer Entity Masking

Use `BaseEntityAdapter` to apply HMAC-SHA256 privacy hashing to customer account IDs locally before data enters network storage:

```python
from cfi_connector_sdk import BaseEntityAdapter

entity_adapter = BaseEntityAdapter(bank_salt="sec_bank_a_salt_9983")
masked_customer_id = entity_adapter.hash_customer_id("ACC-883920192")
print(masked_customer_id) # 64-character SHA-256 HMAC digest
```

---

### 3. Local FL Client Connection & Weight Submission

Use `LocalFLClient` to connect your bank client node to the central CFI coordinator via mTLS and submit Differential Privacy masked updates:

```python
from cfi_connector_sdk import LocalFLClient

client = LocalFLClient(
    bank_id="bank-a",
    coordinator_url="coordinator.cfi-network.internal:50051",
    cert_path="/etc/ssl/certs/bank_a.crt",
    key_path="/etc/ssl/certs/bank_a.key",
    ca_path="/etc/ssl/certs/cfi_ca.crt",
)

client.connect()
response = client.submit_local_weights(
    round_id=1,
    weights={"flat_weights": [0.12, -0.45, 0.88]},
    dp_epsilon=0.5,
    num_samples=1000,
)
print("Submission response:", response)
```
