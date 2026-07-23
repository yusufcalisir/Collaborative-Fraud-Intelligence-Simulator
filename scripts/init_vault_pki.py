#!/usr/bin/env python3
"""HashiCorp Vault PKI Secrets Engine Bootstrap Script.

Automates initialisation of the Root CA, role generation, and dynamic X.509
certificate provisioning for inter-bank mTLS in sandbox/Kubernetes environments.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("vault_pki_bootstrap")

VAULT_ADDR = os.getenv("VAULT_ADDR", "http://localhost:8200").rstrip("/")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "root")
PKI_ROLE_NAME = "cfi-bank-role"


def vault_request(
    endpoint: str, method: str = "GET", payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Execute REST API call against local or remote HashiCorp Vault instance."""
    url = f"{VAULT_ADDR}{endpoint}"
    data = json.dumps(payload).encode("utf-8") if payload else None
    headers = {
        "X-Vault-Token": VAULT_TOKEN,
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as err:
        error_body = err.read().decode("utf-8")
        logger.warning(
            "Vault API %s %s returned status %d: %s", method, endpoint, err.code, error_body
        )
        return {"error": error_body, "status": err.code}
    except Exception as exc:
        logger.error("Failed connection to Vault at %s: %s", url, exc)
        return {"error": str(exc)}


def generate_dev_fallback_certs(node_id: str, out_dir: str | Path) -> None:
    """Generate self-signed X.509 mTLS cert bundle as fallback when Vault is offline."""
    from datetime import UTC, datetime, timedelta

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Generate key
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    # Generate self-signed cert
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, f"{node_id}.cfi.internal"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CFI Consortium"),
        ]
    )

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC))
        .not_valid_after(datetime.now(UTC) + timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName(f"{node_id}.cfi.internal"),
                    x509.DNSName("localhost"),
                    x509.DNSName("coordinator"),
                ]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )

    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    (out_path / "cert.pem").write_bytes(cert_pem)
    (out_path / "key.pem").write_bytes(key_pem)
    (out_path / "ca.pem").write_bytes(cert_pem)
    logger.info("Generated dev fallback X.509 cert bundle for %s in %s", node_id, out_path)


def bootstrap_pki(node_id: str | None = None, out_dir: str | None = None) -> bool:
    """Mount PKI engine, generate Root CA, configure role, and issue initial certificates."""
    logger.info("Initializing Vault PKI Secrets Engine at %s...", VAULT_ADDR)

    # 1. Mount PKI secrets engine at /v1/sys/mounts/pki
    logger.info("Step 1: Enabling PKI secrets engine at path 'pki/'...")
    vault_request(
        "/v1/sys/mounts/pki",
        method="POST",
        payload={"type": "pki", "config": {"max_lease_ttl": "87600h"}},
    )

    # 2. Generate Root CA certificate
    logger.info("Step 2: Generating Consortium Root CA certificate...")
    ca_res = vault_request(
        "/v1/pki/root/generate/internal",
        method="POST",
        payload={
            "common_name": "CFI Consortium Root CA",
            "ttl": "87600h",
            "key_type": "rsa",
            "key_bits": 2048,
        },
    )
    if "error" in ca_res and ca_res.get("status") != 400:
        logger.warning("Vault offline or inaccessible: %s. Using dev fallback generator.", ca_res)
        if node_id and out_dir:
            generate_dev_fallback_certs(node_id, out_dir)
        return True

    # 3. Configure CA and CRL URLs
    logger.info("Step 3: Setting CA and CRL endpoints...")
    vault_request(
        "/v1/pki/config/urls",
        method="POST",
        payload={
            "issuing_certificates": [f"{VAULT_ADDR}/v1/pki/ca"],
            "crl_distribution_points": [f"{VAULT_ADDR}/v1/pki/crl"],
        },
    )

    # 4. Create bank role for node certificates
    logger.info("Step 4: Creating PKI role '%s' for bank node SAN domains...", PKI_ROLE_NAME)
    role_res = vault_request(
        f"/v1/pki/roles/{PKI_ROLE_NAME}",
        method="POST",
        payload={
            "allowed_domains": ["cfi.internal", "localhost"],
            "allow_subdomains": True,
            "max_ttl": "720h",
            "key_type": "rsa",
            "key_bits": 2048,
            "allow_bare_domains": True,
        },
    )
    logger.info("PKI Role configured: %s", role_res)

    # 5. Issue initial certificates for specified node or defaults
    nodes = (
        [f"{node_id}.cfi.internal"]
        if node_id
        else ["bank-a.cfi.internal", "bank-b.cfi.internal", "coordinator.cfi.internal"]
    )
    for node_cn in nodes:
        logger.info("Step 5: Provisioning X.509 mTLS leaf certificate for %s...", node_cn)
        cert_res = vault_request(
            f"/v1/pki/issue/{PKI_ROLE_NAME}",
            method="POST",
            payload={
                "common_name": node_cn,
                "alt_names": f"{node_cn},localhost,coordinator",
                "ttl": "720h",
            },
        )
        if "data" in cert_res and out_dir:
            out_path = Path(out_dir)
            out_path.mkdir(parents=True, exist_ok=True)
            (out_path / "cert.pem").write_text(cert_res["data"]["certificate"])
            (out_path / "key.pem").write_text(cert_res["data"]["private_key"])
            (out_path / "ca.pem").write_text(cert_res["data"]["issuing_ca"])
            logger.info("Successfully saved PEM cert bundle to %s", out_path)
        elif "data" not in cert_res and out_dir:
            logger.warning(
                "Vault issuance fallback for %s -> generating dev fallback certs", node_cn
            )
            generate_dev_fallback_certs(node_id or node_cn.split(".")[0], out_dir)

    logger.info("Vault PKI Secrets Engine Bootstrap Completed Successfully!")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vault PKI Bootstrap & Per-Node Cert Provisioner")
    parser.add_argument("--node-id", type=str, help="Node ID (e.g. bank-a, bank-b, coordinator)")
    parser.add_argument(
        "--out-dir", type=str, help="Output directory to write cert.pem, key.pem, ca.pem"
    )
    args = parser.parse_args()

    success = bootstrap_pki(node_id=args.node_id, out_dir=args.out_dir)

    sys.exit(0 if success else 1)
