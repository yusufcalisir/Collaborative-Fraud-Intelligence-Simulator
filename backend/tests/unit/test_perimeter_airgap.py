# ruff: noqa: E402, TC003
"""Automated Unit Test Suite for Perimeter Security WAF & Air-Gapped Installer."""

from __future__ import annotations

from pathlib import Path

from app.infrastructure.deployment.airgap_installer import AirGapBundleBuilder
from app.infrastructure.security.perimeter_waf import (
    PerimeterWAFGuard,
    WAFRuleCategory,
)


def test_perimeter_waf_request_inspection() -> None:
    """Test WAF filtering for malicious SQLi, XSS, and IP whitelist enforcement."""
    waf = PerimeterWAFGuard(whitelisted_ips=["10.0.0.1"], enforce_whitelist=True)

    # 1. Clean request from whitelisted IP -> Allowed
    res_clean = waf.inspect_request(client_ip="10.0.0.1", body='{"user": "alice"}')
    assert res_clean.allowed is True

    # 2. Non-whitelisted IP -> Blocked
    res_ip = waf.inspect_request(client_ip="192.168.1.100", body='{"user": "alice"}')
    assert res_ip.allowed is False
    assert res_ip.rule_triggered == WAFRuleCategory.IP_WHITELIST

    # 3. SQL Injection pattern -> Blocked
    res_sqli = waf.inspect_request(
        client_ip="10.0.0.1", body="SELECT * FROM users WHERE 1=1; DROP TABLE logs;"
    )
    assert res_sqli.allowed is False
    assert res_sqli.rule_triggered == WAFRuleCategory.SQLI_INJECTION

    # 4. XSS pattern -> Blocked
    res_xss = waf.inspect_request(client_ip="10.0.0.1", body="<script>alert('pwned')</script>")
    assert res_xss.allowed is False
    assert res_xss.rule_triggered == WAFRuleCategory.XSS_ATTACK


def test_airgap_bundle_building_and_checksum_verification(tmp_path: Path) -> None:
    """Test air-gapped deployment bundle generation and SHA-256 manifest verification."""
    builder = AirGapBundleBuilder()

    manifest = builder.build_airgap_bundle(output_dir=tmp_path, target_version="v2.0.0")
    assert manifest.version == "v2.0.0"
    assert len(manifest.sha256_checksum) == 64

    bundle_file = tmp_path / "cfi_airgap_v2.0.0.json"
    manifest_file = tmp_path / "airgap_manifest.json"

    assert bundle_file.exists()
    assert manifest_file.exists()

    # Verify checksum matches manifest
    valid = builder.verify_airgap_bundle(bundle_file=bundle_file, manifest_file=manifest_file)
    assert valid is True

    # Modify bundle file bytes to simulate corruption
    bundle_file.write_bytes(b"corrupted contents")
    invalid = builder.verify_airgap_bundle(bundle_file=bundle_file, manifest_file=manifest_file)
    assert invalid is False
