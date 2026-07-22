# Bank Node Self-Service Onboarding Guide (`cfi-cli`)

This guide provides bank IT infrastructure, security, and enterprise deployment teams with step-by-step instructions to onboard a new bank node into the Collaborative Fraud Intelligence (CFI) consortium network using the `cfi-cli` automation tool.

---

## 1. Integration Overview & Prerequisites

The bank client daemon (`cfi-bank-client`) operates within the bank's isolated private network zone (VPC/Subnet). It requires **zero inbound open listening ports**, communicating outbound only to the central coordinator over Mutual TLS (mTLS 1.3) streaming gRPC (default port: `50051`).

### Prerequisites
- **Python**: $\ge 3.10$ installed locally or within the client container image.
- **Network Connectivity**: Outbound TCP access to the coordinator hostname and port (`50051`).
- **Dependencies**: Install platform requirements: `pip install -r backend/requirements.txt`.

---

## 2. Step 1: Initialize Local Directory & Configuration (`cfi-cli init`)

Run `cfi-cli init` to generate the local configuration template (`bank_config.yaml`) and create required storage directories:

```bash
python scripts/cfi_cli.py init --bank-id bank_alpha --coordinator coordinator.cfi.internal:50051
```

### Output Directory Structure
```
.
├── bank_config.yaml          # Node configuration file
├── certs/                    # Directory for X.509 mTLS certificates
├── data/
│   └── vault/                # Encrypted local AES-256 state vault
└── logs/                     # Local daemon execution logs
```

### Configuration Setup (`bank_config.yaml`)
Edit `bank_config.yaml` to fill in your institution's parameters:
```yaml
bank_id: "bank_alpha"
bank_name: "Alpha Bank Corp"
coordinator_host: "coordinator.cfi.internal"
coordinator_port: 50051

mtls:
  enabled: true
  client_cert_path: "certs/bank.crt"
  client_key_path:  "certs/bank.key"
  ca_cert_path:     "certs/consortium_ca.crt"

vault:
  dir: "data/vault"
  passphrase: "<YOUR_STRONG_VAULT_PASSPHRASE>"
```

---

## 3. Step 2: Generate Certificate Signing Request (`cfi-cli cert generate-csr`)

Generate a 4096-bit RSA private key (`bank.key`) and an X.509 Certificate Signing Request (`bank.csr`) formatted for mTLS authentication:

```bash
python scripts/cfi_cli.py cert generate-csr --bank-id bank_alpha --output-dir ./certs
```

### Output JSON Response
```json
{
  "status": "ok",
  "command": "cert generate-csr",
  "bank_id": "bank_alpha",
  "key_file": "certs/bank.key",
  "csr_file": "certs/bank.csr",
  "key_bits": 4096,
  "signature_algorithm": "SHA256withRSA"
}
```

> [!IMPORTANT]
> Keep `certs/bank.key` secret and secure! Submit `certs/bank.csr` to your consortium CA administrator or HashiCorp Vault PKI engine (`/v1/pki/sign`). Once signed, place `bank.crt` and `consortium_ca.crt` into the `certs/` directory.

---

## 4. Step 3: Verify Network Connectivity & mTLS SLA (`cfi-cli test-connection`)

Test outbound gRPC reachability, network latency, and coordinator readiness:

```bash
python scripts/cfi_cli.py test-connection --host coordinator.cfi.internal --port 50051
```

### Response Attributes
- `tcp_reachable`: `true` indicates TCP handshake succeeded.
- `latency_ms`: Outbound round-trip time (target SLA: $< 100\text{ms}$).
- `latency_sla`: `PASS` or `WARN`.

---

## 5. Step 4: Run Self-Service Integration Sandbox (`cfi-cli sandbox run`)

Benchmark local feature store throughput, data contract normalization, and PyTorch GPU/CPU accelerator compatibility prior to joining active federated training rounds:

```bash
python scripts/cfi_cli.py sandbox run --transactions 5000
```

### Benchmark Output
```json
{
  "status": "ok",
  "command": "sandbox run",
  "transactions_generated": 5000,
  "fraud_transactions": 104,
  "fraud_rate_pct": 2.08,
  "total_elapsed_sec": 0.0421,
  "throughput_tps": 118764.8,
  "throughput_sla": "PASS",
  "hardware": {
    "pytorch_available": true,
    "pytorch_version": "2.4.0",
    "cuda_available": true,
    "cuda_device": "NVIDIA GeForce RTX 4090",
    "recommended_device": "cuda"
  }
}
```

---

## 6. Step 5: Launch Client Daemon (`cfi-bank-client`)

Once sandbox benchmarks and mTLS certificate installation pass, launch the production client daemon:

```bash
python backend/app/infrastructure/client_daemon/daemon.py --config bank_config.yaml
```

Or run via Docker:
```bash
docker run -d \
  --name cfi-bank-client-alpha \
  -v $(pwd)/bank_config.yaml:/app/bank_config.yaml \
  -v $(pwd)/certs:/app/certs \
  -v $(pwd)/data/vault:/app/data/vault \
  cfi-bank-client:latest
```

The daemon will initiate an outbound gRPC stream to the coordinator, complete registration, and join active federated learning rounds automatically.
