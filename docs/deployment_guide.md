# 🌐 Multi-Node Network-Isolated Deployment Guide

This guide details the deployment of the **Collaborative Fraud Intelligence (CFI)** platform in a multi-container, network-isolated topology using `docker-compose.multinode.yml`.

Unlike single-process simulations, this architecture enforces strict network isolation boundaries between participating financial institutions (`bank-a`, `bank-b`) and the central coordinator.

---

## 🏗️ Architecture Overview

```
Bank A Private Subnet (bank-a-net)          Bank B Private Subnet (bank-b-net)
┌──────────────────────────────┐            ┌──────────────────────────────┐
│  cfi-bank-client-a           │            │  cfi-bank-client-b           │
│  - Isolated DB Volume        │            │  - Isolated DB Volume        │
│  - Bank A X.509 Cert         │            │  - Bank B X.509 Cert         │
└────────────┬─────────────────┘            └──────────────┬───────────────┘
             │ consortium-net only                          │ consortium-net only
             └─────────────────────┐  ┌────────────────────┘
                                   ▼  ▼
                    ┌──────────────────────────────┐
                    │  cfi-fl-coordinator          │
                    │  - Central PKI / CA           │
                    │  - Secure Aggregator          │
                    │  - gRPC Target: :50051        │
                    └──────────────────────────────┘
```

### Key Isolation Rules
- **No Direct Inter-Bank Routing**: `cfi-bank-client-a` cannot reach `cfi-bank-client-b` directly. `bank-a-net` and `bank-b-net` are marked `internal: true`.
- **Outbound-Only Communication**: Bank client daemons initiate outbound mTLS connections to the central coordinator over `consortium-net` port 50051. Bank nodes expose no inbound listening ports to the coordinator or external entities.
- **Cryptographic Certificate Isolation**: Each participant container uses a dedicated X.509 mTLS certificate and private key stored in an isolated volume.

---

## 🚀 Step-by-Step Deployment Instructions

### Step 1: Provision Per-Node X.509 PKI Certificates

Before launching containers, generate separate mTLS certificate bundles for each node:

```bash
# Provision Coordinator PKI
python scripts/init_vault_pki.py --node-id coordinator --out-dir pki/coordinator

# Provision Bank A PKI
python scripts/init_vault_pki.py --node-id bank-a --out-dir pki/bank-a

# Provision Bank B PKI
python scripts/init_vault_pki.py --node-id bank-b --out-dir pki/bank-b
```

Each directory will contain:
- `cert.pem`: Node leaf certificate
- `key.pem`: Node RSA private key
- `ca.pem`: Consortium Root CA certificate

---

### Step 2: Validate Docker Compose Configuration

Verify that the multi-node compose file is syntactically valid:

```bash
docker compose -f docker-compose.multinode.yml config
```

---

### Step 3: Launch Multi-Node Stack

Start the coordinator and bank client containers:

```bash
docker compose -f docker-compose.multinode.yml up -d --build
```

---

### Step 4: Verify Container Status & Health

Check that all three containers are healthy and running:

```bash
docker compose -f docker-compose.multinode.yml ps
```

Verify coordinator health endpoint:

```bash
curl http://localhost:8000/health
```

---

### Step 5: Verify Network Isolation Boundaries

Test that Bank A **cannot** communicate directly with Bank B:

```bash
# Expect failure / unreachable host (proving internal subnet isolation)
docker exec cfi-bank-client-a ping -c 2 cfi-bank-client-b
```

Verify that Bank A **can** reach the central coordinator over gRPC port 50051:

```bash
docker exec cfi-bank-client-a nc -zv coordinator 50051
```

---

## 📊 Operations & Telemetry

### Inspecting Container Logs

```bash
# Coordinator logs
docker logs -f cfi-fl-coordinator

# Bank A Client Daemon logs
docker logs -f cfi-bank-client-a

# Bank B Client Daemon logs
docker logs -f cfi-bank-client-b
```

### Stopping the Stack

```bash
docker compose -f docker-compose.multinode.yml down -v
```
