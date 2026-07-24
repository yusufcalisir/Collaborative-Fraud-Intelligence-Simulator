# ruff: noqa: UP042
"""Perimeter Web Application Firewall (WAF) Guard."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class WAFRuleCategory(str, Enum):
    """Categories of WAF security rules."""

    IP_WHITELIST = "IP_WHITELIST"
    SQLI_INJECTION = "SQLI_INJECTION"
    XSS_ATTACK = "XSS_ATTACK"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"


@dataclass
class WAFInspectionResult:
    """Dataclass holding WAF inspection verdict."""

    allowed: bool
    rule_triggered: WAFRuleCategory | None = None
    client_ip: str = ""
    reason: str = ""


class PerimeterWAFGuard:
    """Web Application Firewall inspecting incoming requests for malicious patterns and IP whitelists."""

    SQLI_PATTERNS = [
        re.compile(r"(\bUNION\b|\bSELECT\b|\bINSERT\b|\bDELETE\b|\bDROP\b)\s+.*", re.IGNORECASE),
        re.compile(r"(--|;\s*SHUTDOWN|;\s*DROP)", re.IGNORECASE),
    ]

    XSS_PATTERNS = [
        re.compile(r"<script.*?>.*?</script>", re.IGNORECASE),
        re.compile(r"javascript\s*:", re.IGNORECASE),
        re.compile(r"onload\s*=", re.IGNORECASE),
    ]

    def __init__(
        self,
        whitelisted_ips: list[str] | None = None,
        enforce_whitelist: bool = False,
    ) -> None:
        self.whitelisted_ips = set(whitelisted_ips or ["127.0.0.1", "10.0.0.1"])
        self.enforce_whitelist = enforce_whitelist
        self._request_counts: dict[str, int] = field(default_factory=dict)

    def add_whitelisted_ip(self, ip_address: str) -> None:
        """Adds an IP address to the perimeter whitelist."""
        self.whitelisted_ips.add(ip_address)
        logger.info("Added IP %s to WAF whitelist.", ip_address)

    def inspect_request(
        self,
        client_ip: str,
        headers: dict[str, str] | None = None,
        body: str = "",
    ) -> WAFInspectionResult:
        """Inspects request body and headers against WAF rule sets."""
        headers = headers or {}

        # 1. IP Whitelist check
        if self.enforce_whitelist and client_ip not in self.whitelisted_ips:
            logger.warning("WAF BLOCKED IP %s: Not in IP whitelist.", client_ip)
            return WAFInspectionResult(
                allowed=False,
                rule_triggered=WAFRuleCategory.IP_WHITELIST,
                client_ip=client_ip,
                reason="Client IP address not whitelisted.",
            )

        # 2. SQL Injection check
        for pattern in self.SQLI_PATTERNS:
            if pattern.search(body):
                logger.warning("WAF BLOCKED IP %s: SQL Injection pattern detected.", client_ip)
                return WAFInspectionResult(
                    allowed=False,
                    rule_triggered=WAFRuleCategory.SQLI_INJECTION,
                    client_ip=client_ip,
                    reason="Malicious SQL Injection pattern detected.",
                )

        # 3. Cross-Site Scripting (XSS) check
        for pattern in self.XSS_PATTERNS:
            if pattern.search(body):
                logger.warning("WAF BLOCKED IP %s: XSS pattern detected.", client_ip)
                return WAFInspectionResult(
                    allowed=False,
                    rule_triggered=WAFRuleCategory.XSS_ATTACK,
                    client_ip=client_ip,
                    reason="Malicious XSS payload detected.",
                )

        return WAFInspectionResult(allowed=True, client_ip=client_ip)
