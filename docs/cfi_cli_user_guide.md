# 💻 Official CLI Tooling (`cfi-cli`) User Guide

The `cfi-cli` command-line utility provides enterprise operators, SREs, and DevOps engineers with terminal commands for monitoring platform status, running system health probes, exporting diagnostic bundles, and orchestrating rolling node deployments.

---

## 📌 Installation & Usage

Installed automatically as part of the python package:

```bash
pip install -e .
cfi-cli --help
```

---

## 🛠️ Subcommand Reference

### 1. `cfi-cli status`
Prints JSON operational status summary including current platform version, connected bank nodes, active FL round, and global model AUC.

```bash
$ cfi-cli status
{
  "platform_version": "v2.0.0",
  "status": "HEALTHY",
  "active_bank_nodes": ["bank_alpha", "bank_beta", "bank_gamma"],
  "federated_round": 25,
  "global_model_auc": 0.885
}
```

### 2. `cfi-cli health`
Executes real-time readiness and liveness checks across core platform microservices.

```bash
$ cfi-cli health
{
  "status": "UP",
  "components": {
    "inference_engine": "HEALTHY",
    "federated_coordinator": "HEALTHY",
    "privacy_guard": "HEALTHY",
    "dr_manager": "HEALTHY"
  }
}
```

### 3. `cfi-cli export-diagnostics [--output cfi_diagnostics.json]`
Compiles system logs, latency metrics, and SLA compliance stats into an exportable diagnostic bundle JSON file.

```bash
$ cfi-cli export-diagnostics --output /tmp/diag_bundle.json
Diagnostic bundle exported to: /tmp/diag_bundle.json
```

### 4. `cfi-cli deploy [--target-version v2.1.0]`
Triggers zero-downtime rolling node deployment.
