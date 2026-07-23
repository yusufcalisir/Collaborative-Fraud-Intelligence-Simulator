# Enterprise Payment Stream Benchmark Report

> **Note**: This is the reference template for benchmark results.
> Run `python scripts/run_enterprise_stress_test.py` to generate a timestamped report in `reports/`.

---

## Test Configuration

| Parameter | Value |
|---|---|
| Bank Nodes | 5 |
| Target TPS | 10,000 |
| Batch Size | 100 |
| Duration | 30s |
| Payload Schema | ISO 20022 pacs.008 FIToFICstmrCdtTrf |

---

## Throughput Results

| Metric | Value |
|---|---|
| **Total Transactions Processed** | *(run to populate)* |
| **Peak Throughput (tx/sec)** | *(run to populate)* |
| Error Count | *(run to populate)* |
| Error Rate | *(run to populate)* |

---

## Latency Distribution (per-transaction)

| Percentile | Latency |
|---|---|
| Mean | *(run to populate)* |
| p50 (Median) | *(run to populate)* |
| p99 | *(run to populate)* |

---

## Per-Bank Throughput

| Bank Node | TX/sec |
|---|---|
| `bank_a` | *(run to populate)* |
| `bank_b` | *(run to populate)* |
| `bank_c` | *(run to populate)* |
| `bank_d` | *(run to populate)* |
| `bank_e` | *(run to populate)* |

---

## Conformance Verdict

| Check | Result |
|---|---|
| Error Rate < 0.1% | *(run to populate)* |
| p99 Latency | *(run to populate)* |

---

## How to Run

```bash
# Quick local benchmark (3 banks, 500 TPS, 10 seconds)
python scripts/run_enterprise_stress_test.py \
    --banks 3 \
    --target-tps 500 \
    --duration 10 \
    --output-dir reports/

# Full enterprise benchmark (5 banks, 10,000 TPS, 30 seconds)
python scripts/run_enterprise_stress_test.py \
    --banks 5 \
    --target-tps 10000 \
    --duration 30 \
    --output-dir reports/
```

Results are saved as:
- `reports/benchmark_<TIMESTAMP>.json` — machine-readable results
- `reports/benchmark_<TIMESTAMP>.md` — human-readable Markdown report
