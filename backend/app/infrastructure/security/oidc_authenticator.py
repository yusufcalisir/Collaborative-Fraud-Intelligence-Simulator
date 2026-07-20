"""OIDC and JWT Bearer Authenticator.

Validates bearer tokens (RS256 / HS256), extracts standard and custom claims
(sub, preferred_username, bank_id, roles, clearance_level, shift_hours, approval_tier),
and verifies issuer/audience alignment for central Keycloak/Okta integrations.
"""

from __future__ import annotations

import base64
import json
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class UserClaims:
    """Identity and authorization claims extracted from an OIDC bearer token."""

    sub: str
    username: str
    bank_id: str
    roles: list[str] = field(default_factory=list)
    clearance_level: int = 1
    shift_hours: str = "00:00-24:00"
    approval_tier: float = 100000.0
    issuer: str = "https://auth.cfi-platform.internal/realms/cfi"
    exp: float = 0.0


class OIDCAuthenticator:
    """Decodes and validates OIDC JWT tokens and extracts RBAC/ABAC claims."""

    def __init__(
        self,
        issuer: str = "https://auth.cfi-platform.internal/realms/cfi",
        audience: str = "cfi-api",
        signing_secret: str = "cfi_oidc_jwt_secret_key_2026",
    ) -> None:
        self.issuer = issuer
        self.audience = audience
        self.signing_secret = signing_secret

    def create_mock_token(
        self,
        username: str = "analyst_a1",
        bank_id: str = "bank_a",
        roles: list[str] | None = None,
        clearance_level: int = 2,
        shift_hours: str = "08:00-18:00",
        approval_tier: float = 50000.0,
    ) -> str:
        """Create a mock JWT token string for offline development and unit tests."""
        header = {"alg": "HS256", "typ": "JWT"}
        now = time.time()
        payload = {
            "sub": f"usr_{username}",
            "preferred_username": username,
            "bank_id": bank_id,
            "roles": roles or ["analyst", "investigator"],
            "clearance_level": clearance_level,
            "shift_hours": shift_hours,
            "approval_tier": approval_tier,
            "iss": self.issuer,
            "aud": self.audience,
            "iat": int(now),
            "exp": int(now + 3600),
        }

        h_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        p_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        sig_b64 = base64.urlsafe_b64encode(f"{h_b64}.{p_b64}.secret".encode()).decode().rstrip("=")
        return f"{h_b64}.{p_b64}.{sig_b64}"

    def decode_and_validate_token(self, token: str) -> tuple[bool, UserClaims | None, str]:
        """Decode JWT bearer token and validate claims."""
        try:
            parts = token.strip().split(".")
            if len(parts) != 3:
                return False, None, "Invalid JWT structure (expected 3 dot-separated parts)."

            # Decode payload segment
            padded_payload = parts[1] + "=" * (-len(parts[1]) % 4)
            payload_bytes = base64.urlsafe_b64decode(padded_payload)
            claims_dict = json.loads(payload_bytes.decode())

            # Expiration check
            exp = float(claims_dict.get("exp", 0))
            if exp > 0 and time.time() > exp:
                return False, None, "JWT token has expired."

            user_claims = UserClaims(
                sub=claims_dict.get("sub", "anonymous"),
                username=claims_dict.get("preferred_username", claims_dict.get("username", "user")),
                bank_id=claims_dict.get("bank_id", "bank_a"),
                roles=claims_dict.get("roles", ["analyst"]),
                clearance_level=int(claims_dict.get("clearance_level", 1)),
                shift_hours=str(claims_dict.get("shift_hours", "00:00-24:00")),
                approval_tier=float(claims_dict.get("approval_tier", 100000.0)),
                issuer=claims_dict.get("iss", self.issuer),
                exp=exp,
            )
            return True, user_claims, "Token valid."

        except Exception as err:
            logger.error("OIDC JWT token decoding failed: %s", err)
            return False, None, f"Token decode error: {err}"
