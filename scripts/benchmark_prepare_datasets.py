#!/usr/bin/env python3
"""Public Financial Dataset Pipeline & Non-IID Benchmark Dataset Generator (Section 8.1).

Prepares Non-IID financial transaction dataset splits simulating three distinct bank nodes:
- Bank A: IEEE-CIS e-commerce (~3.5% fraud rate, online merchants, European/US subnets)
- Bank B: PaySim mobile transfer (~0.13% fraud rate, peer-to-peer mobile payments)
- Bank C: Credit Card Fraud (~0.17% extreme imbalance, card-not-present/POS)
"""

from __future__ import annotations

import argparse
import json
import logging
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("benchmark_prepare_datasets")


def generate_bank_a_ieee_cis(samples: int, seed: int = 42) -> pd.DataFrame:
    """Generate Bank A dataset (IEEE-CIS e-commerce, moderate fraud ~3.5%)."""
    rng = np.random.default_rng(seed)
    random.seed(seed)

    n_fraud = max(1, int(samples * 0.035))
    n_legit = samples - n_fraud

    is_fraud = np.array([1] * n_fraud + [0] * n_legit)
    rng.shuffle(is_fraud)

    now = datetime.now(UTC)
    timestamps = [now - timedelta(minutes=int(i * 3.5)) for i in range(samples)]

    amounts = np.where(
        is_fraud == 1,
        rng.lognormal(mean=5.5, sigma=1.0, size=samples),
        rng.lognormal(mean=4.2, sigma=0.8, size=samples),
    )

    mccs = np.where(
        is_fraud == 1,
        rng.choice(["5999", "5732", "4814"], size=samples),
        rng.choice(["5411", "5812", "5912"], size=samples),
    )
    channels = rng.choice(["ONLINE", "MOBILE_WEB"], size=samples, p=[0.7, 0.3])
    countries = rng.choice(["US", "GB", "DE", "CA"], size=samples, p=[0.5, 0.2, 0.2, 0.1])

    df = pd.DataFrame(
        {
            "transaction_id": [f"tx_a_{i:06d}" for i in range(samples)],
            "account_id": [f"acc_a_{rng.integers(1000, 5000)}" for _ in range(samples)],
            "counterparty_account_id": [
                f"merchant_a_{rng.integers(100, 500)}" for _ in range(samples)
            ],
            "amount": np.round(amounts, 2),
            "currency": "USD",
            "timestamp": [ts.isoformat() for ts in timestamps],
            "merchant_category_code": mccs,
            "origin_country": countries,
            "destination_country": countries,
            "device_fingerprint": [f"fp_a_{rng.integers(10000, 99999)}" for _ in range(samples)],
            "ip_subnet": [f"192.168.{rng.integers(1, 50)}.0/24" for _ in range(samples)],
            "channel_type": channels,
            "is_fraud": is_fraud,
            "dataset_source": "IEEE-CIS-Simulated",
        }
    )
    return df


def generate_bank_b_paysim(samples: int, seed: int = 43) -> pd.DataFrame:
    """Generate Bank B dataset (PaySim mobile money transfers, low fraud ~0.13%)."""
    rng = np.random.default_rng(seed)
    random.seed(seed)

    n_fraud = max(1, int(samples * 0.0013))
    n_legit = samples - n_fraud

    is_fraud = np.array([1] * n_fraud + [0] * n_legit)
    rng.shuffle(is_fraud)

    now = datetime.now(UTC)
    timestamps = [now - timedelta(minutes=int(i * 1.5)) for i in range(samples)]

    amounts = np.where(
        is_fraud == 1,
        rng.lognormal(mean=7.0, sigma=1.5, size=samples),
        rng.lognormal(mean=3.5, sigma=1.0, size=samples),
    )

    mccs = np.where(
        is_fraud == 1,
        rng.choice(["6012", "4829"], size=samples),
        rng.choice(["6011", "4814"], size=samples),
    )
    channels = rng.choice(["MOBILE_APP", "P2P_TRANSFER"], size=samples, p=[0.8, 0.2])
    countries = rng.choice(["US", "SG", "IN", "BR"], size=samples, p=[0.4, 0.3, 0.2, 0.1])

    df = pd.DataFrame(
        {
            "transaction_id": [f"tx_b_{i:06d}" for i in range(samples)],
            "account_id": [f"acc_b_{rng.integers(5000, 9000)}" for _ in range(samples)],
            "counterparty_account_id": [
                f"acc_b_{rng.integers(1000, 5000)}" for _ in range(samples)
            ],
            "amount": np.round(amounts, 2),
            "currency": "USD",
            "timestamp": [ts.isoformat() for ts in timestamps],
            "merchant_category_code": mccs,
            "origin_country": countries,
            "destination_country": countries,
            "device_fingerprint": [f"fp_b_{rng.integers(10000, 99999)}" for _ in range(samples)],
            "ip_subnet": [f"10.0.{rng.integers(1, 50)}.0/24" for _ in range(samples)],
            "channel_type": channels,
            "is_fraud": is_fraud,
            "dataset_source": "PaySim-Simulated",
        }
    )
    return df


def generate_bank_c_credit_card(samples: int, seed: int = 44) -> pd.DataFrame:
    """Generate Bank C dataset (Credit Card Fraud, extreme imbalance ~0.17%)."""
    rng = np.random.default_rng(seed)
    random.seed(seed)

    n_fraud = max(1, int(samples * 0.0017))
    n_legit = samples - n_fraud

    is_fraud = np.array([1] * n_fraud + [0] * n_legit)
    rng.shuffle(is_fraud)

    now = datetime.now(UTC)
    timestamps = [now - timedelta(minutes=int(i * 2.0)) for i in range(samples)]

    amounts = np.where(
        is_fraud == 1,
        rng.lognormal(mean=6.0, sigma=1.2, size=samples),
        rng.lognormal(mean=3.0, sigma=0.9, size=samples),
    )

    mccs = np.where(
        is_fraud == 1,
        rng.choice(["5541", "5812", "5999"], size=samples),
        rng.choice(["5411", "5541", "5912"], size=samples),
    )
    channels = rng.choice(["CARD_NOT_PRESENT", "POS"], size=samples, p=[0.6, 0.4])
    countries = rng.choice(["FR", "DE", "ES", "IT"], size=samples, p=[0.4, 0.3, 0.2, 0.1])

    df = pd.DataFrame(
        {
            "transaction_id": [f"tx_c_{i:06d}" for i in range(samples)],
            "account_id": [f"acc_c_{rng.integers(9000, 12000)}" for _ in range(samples)],
            "counterparty_account_id": [
                f"merchant_c_{rng.integers(500, 900)}" for _ in range(samples)
            ],
            "amount": np.round(amounts, 2),
            "currency": "EUR",
            "timestamp": [ts.isoformat() for ts in timestamps],
            "merchant_category_code": mccs,
            "origin_country": countries,
            "destination_country": countries,
            "device_fingerprint": [f"fp_c_{rng.integers(10000, 99999)}" for _ in range(samples)],
            "ip_subnet": [f"172.16.{rng.integers(1, 50)}.0/24" for _ in range(samples)],
            "channel_type": channels,
            "is_fraud": is_fraud,
            "dataset_source": "CreditCard-Simulated",
        }
    )
    return df


def prepare_benchmark_datasets(
    samples: int = 2000, out_dir: str | Path = "storage/benchmark_datasets"
) -> dict[str, Any]:
    """Generates Non-IID benchmark transaction dataset splits and saves Parquet/CSV files."""
    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Preparing Non-IID benchmark datasets (samples=%d)...", samples)

    df_a = generate_bank_a_ieee_cis(samples)
    df_b = generate_bank_b_paysim(samples)
    df_c = generate_bank_c_credit_card(samples)

    manifest = {
        "generated_at": datetime.now(UTC).isoformat(),
        "sample_count_per_bank": samples,
        "banks": {
            "bank_a": {
                "dataset_name": "IEEE-CIS Fraud Detection (Simulated)",
                "fraud_count": int(df_a["is_fraud"].sum()),
                "fraud_rate_pct": float(np.round(df_a["is_fraud"].mean() * 100, 3)),
                "file": "bank_a.parquet",
            },
            "bank_b": {
                "dataset_name": "PaySim Mobile Money (Simulated)",
                "fraud_count": int(df_b["is_fraud"].sum()),
                "fraud_rate_pct": float(np.round(df_b["is_fraud"].mean() * 100, 3)),
                "file": "bank_b.parquet",
            },
            "bank_c": {
                "dataset_name": "Credit Card Fraud (Simulated Extreme Imbalance)",
                "fraud_count": int(df_c["is_fraud"].sum()),
                "fraud_rate_pct": float(np.round(df_c["is_fraud"].mean() * 100, 3)),
                "file": "bank_c.parquet",
            },
        },
    }

    # Write Parquet and CSV fallbacks
    for bank_key, df in [("bank_a", df_a), ("bank_b", df_b), ("bank_c", df_c)]:
        parquet_path = target_dir / f"{bank_key}.parquet"
        csv_path = target_dir / f"{bank_key}.csv"

        try:
            df.to_parquet(parquet_path, index=False)
            logger.info("Saved Parquet dataset: %s (%d rows)", parquet_path, len(df))
        except Exception as err:
            logger.warning("Parquet write unavailable (%s) -> writing CSV fallback", err)

        df.to_csv(csv_path, index=False)
        logger.info("Saved CSV dataset fallback: %s (%d rows)", csv_path, len(df))

    manifest_path = target_dir / "dataset_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info("Saved benchmark manifest: %s", manifest_path)

    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare Non-IID Benchmark Datasets")
    parser.add_argument("--samples", type=int, default=2000, help="Number of samples per bank")
    parser.add_argument(
        "--out-dir", type=str, default="storage/benchmark_datasets", help="Output directory"
    )
    args = parser.parse_args()

    manifest = prepare_benchmark_datasets(samples=args.samples, out_dir=args.out_dir)
    print(json.dumps(manifest, indent=2))
