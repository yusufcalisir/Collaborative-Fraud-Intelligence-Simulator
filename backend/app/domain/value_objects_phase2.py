"""Phase 2 value objects.

Immutable data containers for the AML intelligence platform.
These carry structured data between services without identity.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RiskScore:
    """Composite risk score with breakdown of contributing signals.

    The final score is a weighted combination of independent risk signals.
    Score range: 0 (no risk) to 1000 (maximum risk).
    """

    score: float  # 0-1000
    signals: list[RiskSignal]
    timestamp: str = ""

    @property
    def risk_level(self) -> str:
        if self.score >= 800:
            return "critical"
        if self.score >= 600:
            return "high"
        if self.score >= 400:
            return "medium"
        if self.score >= 200:
            return "low"
        return "minimal"

    @property
    def top_signals(self) -> list[RiskSignal]:
        """Return signals sorted by weighted contribution."""
        return sorted(self.signals, key=lambda s: s.weighted_score, reverse=True)


@dataclass(frozen=True)
class RiskSignal:
    """A single input to the risk scoring pipeline.

    Each signal independently evaluates one aspect of risk.
    The final score combines all signals with configurable weights.
    """

    signal_name: str
    weight: float  # 0.0 to 1.0
    raw_value: float  # Raw signal output
    normalized_score: float  # 0.0 to 1.0
    explanation: str = ""

    @property
    def weighted_score(self) -> float:
        return self.weight * self.normalized_score


@dataclass(frozen=True)
class RiskWeightConfig:
    """Configurable weights for the risk scoring pipeline.

    All weights should sum to approximately 1.0 for interpretability,
    but this is not enforced — weights are relative.
    """

    ml_prediction: float = 0.25
    velocity_rules: float = 0.15
    merchant_reputation: float = 0.10
    country_risk: float = 0.10
    device_anomaly: float = 0.08
    customer_history: float = 0.10
    previous_alerts: float = 0.08
    chargeback_history: float = 0.07
    behavior_anomaly: float = 0.07

    def to_dict(self) -> dict[str, float]:
        return {
            "ml_prediction": self.ml_prediction,
            "velocity_rules": self.velocity_rules,
            "merchant_reputation": self.merchant_reputation,
            "country_risk": self.country_risk,
            "device_anomaly": self.device_anomaly,
            "customer_history": self.customer_history,
            "previous_alerts": self.previous_alerts,
            "chargeback_history": self.chargeback_history,
            "behavior_anomaly": self.behavior_anomaly,
        }


@dataclass(frozen=True)
class ExplainabilityReport:
    """Explains why an alert was generated.

    Provides multiple levels of explanation for investigators:
    feature-level (model inputs), risk-factor-level (business rules),
    and historical evidence.
    """

    alert_id: str
    top_features: list[dict[str, float | str]]  # [{"feature": name, "contribution": value}]
    risk_factors: list[str]  # Human-readable risk descriptions
    historical_evidence: list[str]  # Prior alerts, cases, patterns
    model_confidence: float  # 0.0-1.0
    risk_score_breakdown: list[RiskSignal] = field(default_factory=list)
    explanation_text: str = ""  # Generated human-readable summary


@dataclass(frozen=True)
class AlertReasonCode:
    """A structured reason code for an alert.

    Reason codes provide machine-readable justifications that map
    to specific detection rules or model outputs.
    """

    code: str  # e.g. "VEL-001", "ML-HIGH", "GEO-RISK"
    description: str
    signal_source: str  # Which risk signal generated this
    severity_contribution: float = 0.0  # How much this contributed to severity


@dataclass(frozen=True)
class PrivacyPreservingIdentifier:
    """A deterministic hash of PII that enables cross-institution matching.

    Uses HMAC-SHA256 with a type-specific salt. The same raw identifier
    at different banks produces the same hash, enabling entity resolution
    without exposing the underlying PII.

    Security note: In production, the HMAC key is managed by each tenant's
    isolated KMS/HSM vault.  The ``compute_with_kms`` class method retrieves
    the tenant-specific HMAC key automatically.
    """

    hash_value: str
    entity_type: str
    bank_id: str

    @staticmethod
    def compute(raw_value: str, entity_type: str, hmac_key: str = "fraud-intel-simulator") -> str:
        """Compute a deterministic privacy-preserving hash.

        The hash is deterministic: same input → same output across all banks.
        This enables entity matching without exposing the raw identifier.
        """
        # Type-specific salt prevents cross-type collisions
        salted = f"{entity_type}:{raw_value.strip().lower()}"
        return hmac.new(
            hmac_key.encode(),
            salted.encode(),
            hashlib.sha256,
        ).hexdigest()[:16]  # Truncated for readability in UI

    @classmethod
    def compute_with_kms(cls, raw_value: str, entity_type: str, bank_id: str) -> str:
        """Compute a privacy-preserving hash using the bank's KMS-managed HMAC key.

        Retrieves the tenant-isolated HMAC key from the KMS vault and delegates
        to the standard ``compute`` method.  This ensures each bank's hashing
        is cryptographically independent.
        """
        from app.application.services.kms_service import get_kms_service

        kms = get_kms_service()
        hmac_key = kms.get_hmac_key(bank_id)
        return cls.compute(raw_value, entity_type, hmac_key=hmac_key)


@dataclass(frozen=True)
class IntelligenceSummary:
    """Aggregated statistics about shared intelligence.

    Used for the investigation dashboard to show collaboration health.
    """

    total_intelligence_items: int = 0
    items_by_type: dict[str, int] = field(default_factory=dict)
    items_by_bank: dict[str, int] = field(default_factory=dict)
    avg_risk_indicator: float = 0.0
    cross_institution_matches: int = 0
    active_shared_entities: int = 0


@dataclass(frozen=True)
class GraphSubgraph:
    """A portion of the entity relationship graph for visualization.

    Serialized to React Flow format for the frontend.
    """

    nodes: list[dict] = field(default_factory=list)  # React Flow nodes
    edges: list[dict] = field(default_factory=list)  # React Flow edges
    clusters: list[list[str]] = field(default_factory=list)  # Groups of connected entity IDs
    center_entity_id: str = ""
    depth: int = 2
