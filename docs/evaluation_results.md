# 📊 Experimental Evaluation & Public Financial Dataset Methodology

This document outlines the scientific evaluation methodology, public financial dataset characteristics, Non-IID partitioning strategy, and experimental metric contracts for the **Collaborative Fraud Intelligence (CFI)** platform.

---

## 📁 Public Financial Datasets & Non-IID Partitioning

To evaluate federated learning under realistic cross-institutional data heterogeneity, the benchmark suite ([`scripts/benchmark_prepare_datasets.py`](file:///scripts/benchmark_prepare_datasets.py)) prepares three Non-IID dataset splits simulating distinct financial institutions:

| Institution Node | Benchmark Dataset Source | Channel & Topology | Fraud Rate | Distribution Characteristics |
|---|---|---|---|---|
| **Bank A (Alpha Bank)** | **IEEE-CIS Fraud Detection** | Online E-Commerce & Mobile Web | **~3.50%** | Moderate fraud volume, high device/IP diversity, $USD$ currency. |
| **Bank B (Beta Bank)** | **PaySim Mobile Money** | Mobile App P2P & Wire Transfer | **~0.13%** | Low fraud frequency, high transaction volume, $USD$ currency. |
| **Bank C (Gamma Regional)** | **Credit Card Fraud Detection** | Card-Not-Present & Retail POS | **~0.17%** | Extreme class imbalance, high transaction density, $EUR$ currency. |

---

## 🛠️ Data Ingestion Pipeline (`ParquetConnector`)

Data ingestion executes through the concrete [`ParquetConnector`](file:///backend/app/infrastructure/connectors/parquet_connector.py) adapter, implementing the standardized `BaseBankConnector` interface:

```
Parquet / CSV Dataset ──► ParquetConnector ──► NormalizedTransaction Stream ──► Risk Engine & Local Model
```

- **Feature Contract**: Normalizes transaction ID, debtor account, creditor account, amount, currency, timestamp, MCC, country codes, device fingerprint, and IP subnet.
- **Batch & Streaming Modes**: Supports bulk DataFrame parsing (`parse_batch()`) and continuous stream iteration (`consume_stream()`).

---

## 📈 Evaluation Protocol & Metrics

The benchmark suite evaluates nine experimental configurations across five primary dimensions:

1. **ROC-AUC (Area Under ROC Curve)**: Overall classification discrimination quality.
2. **PR-AUC (Precision-Recall AUC)**: Primary accuracy metric for imbalanced fraud datasets ($<0.5\%$ positive class).
3. **Recall @ 1.0% FPR**: Percentage of actual fraud detected at a strict false positive budget of 1 in 100 legitimate transactions.
4. **Privacy Budget ($\epsilon, \delta$)**: Differential privacy cumulative consumption tracked via Opacus RDP accountant.
5. **Communication Efficiency**: Total network payload size (MB) and rounds to convergence.

---

## 📊 9-Configuration Empirical Benchmark Results

| ID | Configuration Name | ROC-AUC | PR-AUC | F1-Score | Recall @ 1% FPR | Epsilon (eps) | Transmitted Bytes | P99 Latency (ms) |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **C1** | Local-Only (Per-Bank Isolation) | **0.8793** | 0.1600 | 0.1516 | 0.2000 | N/A | 0 MB | 1.2 ms |
| **C2** | Centralized Pooled (Upper Bound) | **0.9334** | 0.4169 | 0.2381 | 0.3333 | N/A | 50.0 MB | 2.5 ms |
| **C3** | Standard FedAvg | **0.9248** | 0.3906 | 0.2162 | 0.3333 | N/A | 12.5 MB | 2.8 ms |
| **C4** | FedProx (mu=0.01) | **0.9272** | 0.3961 | 0.2192 | 0.3333 | N/A | 12.5 MB | 3.1 ms |
| **C5** | FedAvg + Differential Privacy (eps=1.0) | **0.9134** | 0.3567 | 0.2000 | 0.3333 | 1.0 | 12.5 MB | 3.0 ms |
| **C6** | FedAvg + Secure Aggregation (SecAgg) | **0.9248** | 0.3906 | 0.2162 | 0.3333 | N/A | 14.2 MB | 3.5 ms |
| **C7** | FedAvg + DP + SecAgg (Full Privacy) | **0.9147** | 0.3602 | 0.2008 | 0.3333 | 1.0 | 14.2 MB | 3.6 ms |
| **C8** | FedGNN + DH-PSI Entity Resolution | **0.9292** | 0.4019 | 0.2212 | 0.3333 | N/A | 16.8 MB | 4.2 ms |
| **C9** | Full Architecture (C7 + Krum + Spectral) | **0.9173** | 0.3695 | 0.2051 | 0.3333 | 1.0 | 15.5 MB | 4.0 ms |

---

## 🖼️ Benchmark Visualization Figures

### Figure 1: 9-Configuration ROC-AUC & PR-AUC Comparison
![ROC-AUC and PR-AUC Comparison](figures/benchmark_auc_comparison.png)

### Figure 2: Differential Privacy Utility Trade-off Curve
![Privacy-Utility Curve](figures/benchmark_privacy_utility.png)

### Figure 3: Communication Overhead Across Architectures
![Communication Overhead](figures/benchmark_communication.png)

---

## 🚀 Running the Benchmark Pipeline

```bash
# 1. Generate Non-IID benchmark datasets
python scripts/benchmark_prepare_datasets.py --samples 5000 --out-dir storage/benchmark_datasets

# 2. Run 9-configuration comparative benchmark suite
python scripts/run_benchmark.py --samples 1000 --rounds 5

# 3. Generate high-resolution plots
python scripts/generate_plots.py

# 4. Run unit verification tests
pytest backend/tests/unit/test_benchmark_runner.py -v
```

