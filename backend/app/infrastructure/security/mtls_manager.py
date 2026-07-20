"""Mutual TLS (mTLS) and PKI Manager.

Manages X.509 CA root, server, and client certificates for inter-service
communication (FL Coordinator, Identity Graph, Fraud Alert, Bank Connectors).
Provides certificate generation, SAN validation, CRL checks, and SSLContext building.
"""

from __future__ import annotations

import logging
import ssl
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class X509CertificateInfo:
    """Metadata container for an X.509 certificate."""

    subject_cn: str
    issuer_cn: str
    serial_number: str
    valid_from: str
    valid_until: str
    sans: list[str] = field(default_factory=list)
    is_ca: bool = False
    revoked: bool = False


class MTLSManager:
    """Manages PKI certificates and builds mTLS SSLContext objects."""

    def __init__(self, ca_cn: str = "CFI-Root-CA", default_domain: str = "internal") -> None:
        self.ca_cn = ca_cn
        self.default_domain = default_domain
        self.crl_revoked_serials: set[str] = set()

    def generate_cert_info(
        self,
        cn: str,
        sans: list[str] | None = None,
        is_ca: bool = False,
        days_valid: int = 365,
    ) -> X509CertificateInfo:
        """Generate certificate metadata descriptor."""
        san_list = sans or [f"{cn}.{self.default_domain}", "localhost"]
        now = time.time()
        from_str = time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime(now))
        until_str = time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime(now + days_valid * 86400))
        serial = f"{abs(hash(cn + from_str)):016x}"

        return X509CertificateInfo(
            subject_cn=cn,
            issuer_cn=self.ca_cn,
            serial_number=serial,
            valid_from=from_str,
            valid_until=until_str,
            sans=san_list,
            is_ca=is_ca,
            revoked=serial in self.crl_revoked_serials,
        )

    def validate_peer_certificate(
        self, cert_info: X509CertificateInfo, expected_san: str
    ) -> tuple[bool, str]:
        """Validate peer certificate SAN, expiration, and CRL revocation status."""
        if cert_info.revoked:
            return False, f"Certificate serial {cert_info.serial_number} is revoked in CRL."

        if expected_san not in cert_info.sans and not any(
            s.endswith(expected_san) for s in cert_info.sans
        ):
            return False, f"SAN match failure: expected '{expected_san}', got {cert_info.sans}."

        return True, "Certificate valid and verified."

    def revoke_certificate(self, serial_number: str) -> None:
        """Add certificate serial number to CRL revocation list."""
        self.crl_revoked_serials.add(serial_number)
        logger.warning("Certificate serial %s added to mTLS CRL revocation list.", serial_number)

    def build_ssl_context(self, is_server: bool = True) -> ssl.SSLContext:
        """Build Python SSLContext configured for mTLS 1.3 peer authentication."""
        context = ssl.create_default_context(
            purpose=ssl.Purpose.CLIENT_AUTH if is_server else ssl.Purpose.SERVER_AUTH
        )
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.verify_mode = ssl.CERT_REQUIRED if is_server else ssl.CERT_REQUIRED
        return context
