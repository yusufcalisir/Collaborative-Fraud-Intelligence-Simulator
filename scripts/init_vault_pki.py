#!/usr/bin/env python3
"""HashiCorp Vault PKI Secrets Engine Bootstrap Script.

Automates initialisation of the Root CA, role generation, and dynamic X.509
certificate provisioning for inter-bank mTLS in sandbox/Kubernetes environments.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import urllib.error
import urllib.request
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("vault_pki_bootstrap")

VAULT_ADDR = os.getenv("VAULT_ADDR", "http://localhost:8200").rstrip("/")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "root")
PKI_ROLE_NAME = "cfi-bank-role"


def vault_request(endpoint: str, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
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
        logger.warning("Vault API %s %s returned status %d: %s", method, endpoint, err.code, error_body)
        return {"error": error_body, "status": err.code}
    except Exception as exc:
        logger.error("Failed connection to Vault at %s: %s", url, exc)
        return {"error": str(exc)}


def bootstrap_pki() -> bool:
    """Mount PKI engine, generate Root CA, configure role, and issue initial certificates."""
    logger.info("Initializing Vault PKI Secrets Engine at %s...", VAULT_ADDR)

    # 1. Mount PKI secrets engine at /v1/sys/mounts/pki
    logger.info("Step 1: Enabling PKI secrets engine at path 'pki/'...")
    vault_request("/v1/sys/mounts/pki", method="POST", payload={"type": "pki", "config": {"max_lease_ttl": "87600h"}})

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
        logger.error("Failed to generate Root CA: %s", ca_res)
        return False

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

    # 5. Issue initial certificates for Bank A, Bank B, and Coordinator
    nodes = ["bank-a.cfi.internal", "bank-b.cfi.internal", "coordinator.cfi.internal"]
    for node_cn in nodes:
        logger.info("Step 5: Provisioning initial X.509 mTLS leaf certificate for %s...", node_cn)
        cert_res = vault_request(
            f"/v1/pki/issue/{PKI_ROLE_NAME}",
            method="POST",
            payload={
                "common_name": node_cn,
                "alt_names": f"{node_cn},localhost",
                "ttl": "720h",
            },
        )
        if "data" in cert_res:
            serial = cert_res["data"].get("serial_number")
            logger.info("Successfully provisioned X.509 cert for %s (Serial: %s)", node_cn, serial)
        else:
            logger.warning("Could not issue cert for %s (Vault offline or dev mock fallback): %s", node_cn, cert_res)

    logger.info("Vault PKI Secrets Engine Bootstrap Completed Successfully!")
    return True


if __name__ == "__main__":
    success = bootstrap_pki()
    sys.exit(0 if success else 1)
