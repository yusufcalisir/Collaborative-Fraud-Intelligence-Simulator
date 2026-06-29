"""Domain enumerations.

Defines the bounded vocabulary for simulation states, bank tiers,
and aggregation strategies used throughout the system.
"""

from enum import StrEnum


class SimulationStatus(StrEnum):
    """Lifecycle states of a simulation run."""

    PENDING = "pending"
    GENERATING_DATA = "generating_data"
    TRAINING_LOCAL = "training_local"
    TRAINING_FEDERATED = "training_federated"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"


class BankTier(StrEnum):
    """Bank size classification affecting data volume and distribution."""

    LARGE = "large"
    MEDIUM = "medium"
    SMALL = "small"


class ModelType(StrEnum):
    """Whether a model was trained locally or via federation."""

    LOCAL = "local"
    FEDERATED = "federated"


class AggregationMethod(StrEnum):
    """Supported federated aggregation strategies."""

    FED_AVG = "fed_avg"
    FED_AVG_WEIGHTED = "fed_avg_weighted"


class ClientStatus(StrEnum):
    """Status of a bank client during a training round."""

    ACTIVE = "active"
    DROPPED = "dropped"
    RECONNECTED = "reconnected"
    OFFLINE = "offline"


class PrivacyMechanism(StrEnum):
    """Available privacy-enhancing mechanisms."""

    NONE = "none"
    DIFFERENTIAL_PRIVACY = "differential_privacy"
    SECURE_AGGREGATION = "secure_aggregation"
    BOTH = "both"


# ── Phase 2: AML Intelligence Platform ────────


class AlertSeverity(StrEnum):
    """Severity classification for fraud alerts."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(StrEnum):
    """Lifecycle states of a fraud alert."""

    NEW = "new"
    INVESTIGATING = "investigating"
    CONFIRMED_FRAUD = "confirmed_fraud"
    FALSE_POSITIVE = "false_positive"
    ESCALATED = "escalated"
    CLOSED = "closed"


class CaseStatus(StrEnum):
    """Lifecycle states of an investigation case."""

    OPEN = "open"
    ASSIGNED = "assigned"
    INVESTIGATING = "investigating"
    PENDING_REVIEW = "pending_review"
    ESCALATED = "escalated"
    CLOSED_CONFIRMED = "closed_confirmed"
    CLOSED_FALSE_POSITIVE = "closed_false_positive"


class CasePriority(StrEnum):
    """Priority classification for investigation cases."""

    P1_CRITICAL = "p1_critical"
    P2_HIGH = "p2_high"
    P3_MEDIUM = "p3_medium"
    P4_LOW = "p4_low"


class EntityType(StrEnum):
    """Types of entities in the financial crime graph."""

    CUSTOMER = "customer"
    MERCHANT = "merchant"
    DEVICE = "device"
    CARD = "card"
    EMAIL = "email"
    PHONE = "phone"
    IP_ADDRESS = "ip_address"


class RelationshipType(StrEnum):
    """Types of edges in the entity relationship graph."""

    OWNS = "owns"
    USES = "uses"
    TRANSACTS_WITH = "transacts_with"
    SHARES_DEVICE = "shares_device"
    SHARES_IP = "shares_ip"
    LINKED_ALERT = "linked_alert"
    SAME_ENTITY = "same_entity"


class RiskLevel(StrEnum):
    """Risk classification for entities and transactions."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"


class IntelligenceType(StrEnum):
    """Types of shared intelligence between institutions."""

    FRAUD_ALERT = "fraud_alert"
    PATTERN_MATCH = "pattern_match"
    VELOCITY_ANOMALY = "velocity_anomaly"
    ENTITY_LINK = "entity_link"
    RISK_SCORE_CHANGE = "risk_score_change"


class ScenarioType(StrEnum):
    """Pre-built fraud scenario types for simulation."""

    FRAUD_RING = "fraud_ring"
    ACCOUNT_TAKEOVER = "account_takeover"
    MONEY_LAUNDERING = "money_laundering"
    CARD_TESTING = "card_testing"
