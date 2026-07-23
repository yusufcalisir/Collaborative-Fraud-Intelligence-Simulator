# ruff: noqa: E402
#!/usr/bin/env python3
"""Reference Bank Connector Implementation using cfi-connector-sdk."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

# Ensure sdk/python is in sys.path when executed standalone
sdk_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "python")
)
if sdk_path not in sys.path:
    sys.path.insert(0, sdk_path)

from cfi_connector_sdk import (
    BaseEntityAdapter,
    BaseFeatureAdapter,
    BaseTransactionAdapter,
    ConnectorHealthMonitor,
    LocalFLClient,
    NormalizedTransaction,
)


class CoreBankingPaymentAdapter(BaseTransactionAdapter):
    """Reference transaction adapter mapping sample core banking feeds to NormalizedTransaction."""

    def parse_native_payload(self, payload: dict[str, Any]) -> NormalizedTransaction:
        return NormalizedTransaction(
            transaction_id=str(payload["tx_ref"]),
            account_id=str(payload["debtor_iban"]),
            counterparty_account_id=str(payload["creditor_iban"]),
            amount=float(payload["amount"]),
            currency=str(payload.get("currency", "USD")),
            merchant_category_code=str(payload.get("mcc", "5411")),
            channel_type=str(payload.get("channel", "ONLINE")),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Reference Bank Connector Execution Script")
    parser.add_argument("--bank-id", default="bank-a", help="Unique bank node identifier")
    parser.add_argument("--salt", default="sec_bank_a_salt", help="Bank HMAC privacy salt")
    parser.add_argument("--broker-host", default="localhost", help="Message broker host")
    parser.add_argument("--broker-port", type=int, default=5672, help="Message broker port")
    args = parser.parse_args()

    print(f"=== Starting Reference Bank Connector for '{args.bank_id}' ===")

    # 1. Health Probe
    monitor = ConnectorHealthMonitor(broker_host=args.broker_host, broker_port=args.broker_port)
    report = monitor.get_health_report()
    print(f"[HEALTH CHECK] Status: {report.status} | Broker Connected: {report.broker_connected}")

    # 2. Transaction Adapter & Entity Hashing
    tx_adapter = CoreBankingPaymentAdapter()
    entity_adapter = BaseEntityAdapter(bank_salt=args.salt)
    feature_adapter = BaseFeatureAdapter()

    sample_raw_feed = {
        "tx_ref": "PAY-8829102",
        "debtor_iban": "DE89370400440532013000",
        "creditor_iban": "FR7630006000011234567890189",
        "amount": 4250.00,
        "currency": "EUR",
        "mcc": "6012",
        "channel": "MOBILE",
    }

    norm_tx = tx_adapter.parse_native_payload(sample_raw_feed)
    hashed_debtor = entity_adapter.hash_customer_id(norm_tx.account_id)
    features = feature_adapter.extract_velocity_features(norm_tx, history=[])

    print(f"[PARSED TX] ID: {norm_tx.transaction_id} | Amount: {norm_tx.amount} {norm_tx.currency}")
    print(f"[PRIVACY HASH] Debtor HMAC: {hashed_debtor[:16]}... (masked 64-char hex)")
    print(f"[VELOCITY FEATURES] 24h Count: {features['tx_count_24h']} | Sum: {features['amount_sum_24h']}")

    # 3. Local FL Client Connection
    fl_client = LocalFLClient(bank_id=args.bank_id)
    fl_client.connect()
    submission = fl_client.submit_local_weights(
        round_id=1,
        weights={"layers": [0.05, -0.12, 0.44]},
        dp_epsilon=0.5,
        num_samples=100,
    )
    print(f"[FL SUBMISSION] Result: {submission['status']} for Round {submission['round_id']}")
    print("=== Reference Bank Connector Execution Complete ===")


if __name__ == "__main__":
    main()
