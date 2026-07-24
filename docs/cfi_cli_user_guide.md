# 💻 Official CLI Tooling (`cfi-cli`) User Guide

The `cfi-cli` command-line utility provides enterprise operators, SREs, and DevOps engineers
with terminal commands for bank node onboarding, live status monitoring, certificate rotation,
signed diagnostic export, health probing, and rolling deployments.

---

## 📌 Installation & Usage

Installed automatically as part of the Python package:

```bash
pip install -e .
cfi-cli --help
```

---

## 🛠️ Subcommand Reference

### 1. `cfi-cli join`

Registers a new bank node with the CF-Intelligence coordinator. On success:
- Saves the issued mTLS certificate → `~/.cfi/certs/{bank_id}.crt`
- Saves the private key → `~/.cfi/certs/{bank_id}.key`
- Saves the connector config YAML → `~/.cfi/config/{bank_id}.yaml`
- Writes active bank pointer → `~/.cfi/config/active_bank`

```bash
cfi-cli join \
  --bank-id bank_alpha \
  --coordinator-url https://coordinator.cf-intelligence.io \
  --legal-name "Alpha National Bank" \
  --jurisdiction TR \
  --contact-email security@alphabank.com \
  --data-residency-region eu-west-1
```

**Expected output:**
```
✅ Bank 'bank_alpha' registered successfully.
   Cert   → /home/ops/.cfi/certs/bank_alpha.crt
   Key    → /home/ops/.cfi/certs/bank_alpha.key
   Config → /home/ops/.cfi/config/bank_alpha.yaml
   Run: cfi-cli start-daemon --bank-id bank_alpha
```

**Error — already registered:**
```
ℹ️  Bank 'bank_alpha' is already registered at https://coordinator.cf-intelligence.io.
   Run: cfi-cli status to check its state.
```

| Flag | Required | Description |
|---|---|---|
| `--bank-id` | ✅ | Unique bank node identifier (3-36 alphanumeric chars, hyphens, underscores) |
| `--coordinator-url` | ✅ | Base URL of the CF-Intelligence coordinator |
| `--legal-name` | ✅ | Full legal institution name |
| `--jurisdiction` | ✅ | ISO 3166-1 alpha-2 country code (e.g. `TR`, `US`, `DE`) |
| `--contact-email` | ✅ | Primary security contact email |
| `--data-residency-region` | ✅ | Regulatory cloud region (e.g. `eu-west-1`) |

---

### 2. `cfi-cli status`

Queries live bank node status from the coordinator. Reads `~/.cfi/config/active_bank`
to determine which bank and coordinator URL to query.

```bash
cfi-cli status
```

**Expected output:**
```
┌─ Bank Status ────────────────────────────────────────
│  bank_id        : bank_alpha
│  legal_name     : Alpha National Bank
│  jurisdiction   : TR
│  status         : ACTIVE
│  cert_fingerprint: abc123def456789012...
│  activated_at   : 2026-07-24T18:05:00
└──────────────────────────────────────────────────────
```

> **Note:** If no `active_bank` config is found (e.g. before running `join`),
> a local stub is printed with a reminder to run `cfi-cli join` first.

---

### 3. `cfi-cli rotate-certs`

Rotates the mTLS certificate for an active bank node. Overwrites the existing
cert and key files on disk.

```bash
cfi-cli rotate-certs --bank-id bank_alpha
```

**Expected output:**
```
✅ Certificate rotated for 'bank_alpha'.
   Fingerprint: d4e5f6a7b8c9...
   Cert saved → /home/ops/.cfi/certs/bank_alpha.crt
```

| Flag | Required | Description |
|---|---|---|
| `--bank-id` | ✅ | Bank node to rotate the certificate for |

> **Error — no active bank configured:**
> ```
> ❌ Error: No active_bank config found. Run 'cfi-cli join' first or set CFI_HOME.
> ```

---

### 4. `cfi-cli export-diagnostics [--output PATH]`

Collects system diagnostics (hostname, OS, Python version, active bank ID, cert
file mtime, SLA metrics) and writes a SHA-256 signed JSON bundle.

```bash
cfi-cli export-diagnostics --output /tmp/diag_bundle.json
```

**Expected output:**
```
✅ Diagnostics bundle saved to /tmp/diag_bundle.json
   SHA-256: 3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e
```

**Bundle structure:**
```json
{
  "cli_version": "v2.0.0",
  "hostname": "ops-node-01.prod.internal",
  "os": "Linux-6.1.0-x86_64",
  "python_version": "3.12.10",
  "active_bank_id": "bank_alpha",
  "cert_file_mtime": 1753387200.0,
  "logs": ["No critical errors encountered.", "SLA compliance 99.95%."],
  "metrics": { "p95_latency_ms": 42.5, "error_budget_remaining_pct": 100.0 },
  "sha256_signature": "<hex digest of the above fields sorted by key>"
}
```

| Flag | Default | Description |
|---|---|---|
| `--output` | `cfi_diagnostics.json` | Output filepath for the diagnostic bundle |

---

### 5. `cfi-cli health`

Executes real-time readiness and liveness checks across core platform microservices.

```bash
cfi-cli health
```

**Expected output:**
```json
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

---

### 6. `cfi-cli deploy [--target-version v2.1.0]`

Triggers zero-downtime rolling node deployment.

```bash
cfi-cli deploy --target-version v2.2.0
```

**Expected output:**
```json
{
  "target_version": "v2.2.0",
  "stage": "DRAINING_CONNECTIONS",
  "message": "Rolling deployment to v2.2.0 initiated."
}
```

---

## 🔧 Environment Variables

| Variable | Default | Description |
|---|---|---|
| `CFI_HOME` | `~/.cfi` | Root directory for certs, configs, and active bank pointer |

---

## ❌ Common Errors

| Error | Cause | Fix |
|---|---|---|
| `No active_bank config found` | `join` not yet run | Run `cfi-cli join --bank-id ... --coordinator-url ...` |
| `HTTP 409 from .../register` | Bank ID already exists | Check with `cfi-cli status` or use a different `--bank-id` |
| `Connection failed to ...` | Coordinator unreachable | Verify network, VPN, and port 443 access |
