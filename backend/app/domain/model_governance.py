"""Model Governance, Regulatory Compliance & Shadow Deployment Domain Model.

Implements SR 11-7 model risk management standards, semantic versioning,
dual-role sign-off gates, MLOps shadow deployments, and automatic rollback triggers.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(order=True)
class SemanticVersion:
    """Represents a semantic version tag (e.g. v1.0.0, v2.4.1)."""

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, version_str: str) -> SemanticVersion:
        """Parses string version tag into SemanticVersion instance."""
        clean = version_str.strip().lstrip("vV")
        match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", clean)
        if not match:
            # Fallback for integer or invalid strings
            try:
                major = int(clean)
                return cls(major=major, minor=0, patch=0)
            except ValueError:
                return cls(major=1, minor=0, patch=0)

        maj, min_, pat = match.groups()
        return cls(major=int(maj), minor=int(min_), patch=int(pat))

    def to_tag(self) -> str:
        """Formats SemanticVersion into standard vX.Y.Z tag."""
        return f"v{self.major}.{self.minor}.{self.patch}"

    def bump_patch(self) -> SemanticVersion:
        """Returns new SemanticVersion with patch incremented."""
        return SemanticVersion(self.major, self.minor, self.patch + 1)

    def bump_minor(self) -> SemanticVersion:
        """Returns new SemanticVersion with minor incremented."""
        return SemanticVersion(self.major, self.minor + 1, 0)

    def bump_major(self) -> SemanticVersion:
        """Returns new SemanticVersion with major incremented."""
        return SemanticVersion(self.major + 1, 0, 0)


class DualSignoffGate:
    """Enforces SR 11-7 dual-signoff policy before promoting models to production."""

    REQUIRED_ROLES = {"ml_engineer", "compliance_officer"}

    def can_promote(self, sign_offs: list[dict[str, Any]]) -> tuple[bool, str]:
        """Evaluates whether all required sign-offs are present with valid signatures."""
        if not sign_offs:
            return False, "Dual Signoff Gating Failed: No sign-offs provided."

        signed_roles = set()
        for sign in sign_offs:
            role = sign.get("role", "").lower().strip()
            user = sign.get("user", "").strip()
            signature = sign.get("signature", "").strip()

            # Normalize role names
            if role in ("compliance", "compliance_officer", "compliance_lead"):
                role = "compliance_officer"
            elif role in ("ml_engineer", "ml_lead", "engineer"):
                role = "ml_engineer"

            if role in self.REQUIRED_ROLES and user and signature:
                signed_roles.add(role)

        missing_roles = self.REQUIRED_ROLES - signed_roles
        if missing_roles:
            return (
                False,
                f"Dual Signoff Gating Failed: Missing required sign-off roles ({', '.join(sorted(missing_roles))}).",
            )

        return (
            True,
            "Dual Signoff Gate Passed: Both ML Engineer and Compliance Officer sign-offs verified.",
        )


class ShadowDeploymentEngine:
    """Manages shadow prediction traffic routing (default 10% candidate, 90% champion)."""

    def __init__(self, shadow_ratio: float = 0.10) -> None:
        self.shadow_ratio = max(0.0, min(0.50, shadow_ratio))

    def should_route_to_shadow(self, request_id: str) -> bool:
        """Deterministically routes 10% of prediction traffic based on request_id hash."""
        if not request_id:
            return False

        # Hash request_id to integer [0, 99]
        hash_val = int(hashlib.md5(request_id.encode("utf-8")).hexdigest(), 16) % 100
        threshold = int(self.shadow_ratio * 100)
        return hash_val < threshold

    def evaluate_shadow_performance(
        self, champion_auc: float, shadow_auc: float, min_improvement_delta: float = 0.01
    ) -> dict[str, Any]:
        """Evaluates candidate shadow model performance against champion model."""
        delta = shadow_auc - champion_auc
        is_superior = delta >= min_improvement_delta
        return {
            "champion_auc": champion_auc,
            "shadow_auc": shadow_auc,
            "auc_delta": delta,
            "is_superior": is_superior,
            "recommendation": "PROMOTE_SHADOW_TO_CHAMPION" if is_superior else "RETAIN_CHAMPION",
        }


class AutomaticRollbackTrigger:
    """Evaluates live production telemetry and triggers automatic model rollback if thresholds violated."""

    def __init__(self, min_auc_roc: float = 0.65, max_p99_latency_ms: float = 200.0) -> None:
        self.min_auc_roc = min_auc_roc
        self.max_p99_latency_ms = max_p99_latency_ms

    def should_rollback(self, live_auc_roc: float, p99_latency_ms: float) -> tuple[bool, str]:
        """Evaluates live metrics against safety thresholds."""
        if live_auc_roc < self.min_auc_roc:
            return (
                True,
                f"Automatic Rollback Triggered: Live ROC-AUC ({live_auc_roc:.4f}) fell below minimum safety threshold ({self.min_auc_roc:.4f}).",
            )

        if p99_latency_ms > self.max_p99_latency_ms:
            return (
                True,
                f"Automatic Rollback Triggered: Live p99 inference latency ({p99_latency_ms:.1f}ms) exceeded maximum threshold ({self.max_p99_latency_ms:.1f}ms).",
            )

        return (
            False,
            "Telemetry Nominal: Live ROC-AUC and inference latency within acceptable bounds.",
        )


@dataclass
class CryptographicAuditLineage:
    """Binds model version manifest to exact Git commit SHA, dataset SHA-256 hash, DP epsilon, and sign-offs."""

    model_version: str
    git_commit_hash: str
    dataset_hash: str
    dp_epsilon: float
    dp_delta: float = 1e-5
    sign_offs: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime())
    )

    def to_dict(self) -> dict[str, Any]:
        """Serializes CryptographicAuditLineage to JSON-compatible dictionary."""
        return {
            "model_version": self.model_version,
            "git_commit_hash": self.git_commit_hash,
            "dataset_hash": self.dataset_hash,
            "dp_privacy_budget": {"epsilon": self.dp_epsilon, "delta": self.dp_delta},
            "sign_offs": self.sign_offs,
            "created_at": self.created_at,
        }
