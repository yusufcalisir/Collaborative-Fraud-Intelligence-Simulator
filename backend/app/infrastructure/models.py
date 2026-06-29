"""SQLAlchemy ORM models.

These map domain concepts to PostgreSQL tables. They're separate from
domain entities — the repository layer handles conversion between
ORM models and domain objects.

Uses SQLAlchemy 2.0 Mapped/mapped_column syntax.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class SimulationRunModel(Base):
    """Persistent record of a simulation run."""

    __tablename__ = "simulation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    current_round: Mapped[int] = mapped_column(Integer, default=0)
    total_rounds: Mapped[int] = mapped_column(Integer, default=10)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Denormalized results stored as JSON for simplicity.
    # In a production system, these would be normalized into separate tables.
    banks_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    rounds_data: Mapped[list] = mapped_column(JSON, nullable=False, default=list)


class BankConfigModel(Base):
    """Bank configuration for a simulation."""

    __tablename__ = "bank_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    simulation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    fraud_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    num_transactions: Mapped[int] = mapped_column(Integer, nullable=False)
    data_profile: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    local_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    federated_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class TrainingRoundModel(Base):
    """Record of a single federated training round."""

    __tablename__ = "training_rounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    simulation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    global_loss: Mapped[float] = mapped_column(Float, default=0.0)
    participating_bank_ids: Mapped[list] = mapped_column(JSON, default=list)
    dropped_bank_ids: Mapped[list] = mapped_column(JSON, default=list)
    per_bank_loss: Mapped[dict] = mapped_column(JSON, default=dict)
    per_bank_samples: Mapped[dict] = mapped_column(JSON, default=dict)
    aggregation_time_ms: Mapped[float] = mapped_column(Float, default=0.0)
    round_duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ── Phase 2: AML Intelligence Platform ────────


class AlertModel(Base):
    """Persistent record of a fraud alert."""

    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    bank_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(String(36), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="new")
    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    involved_entity_ids: Mapped[list] = mapped_column(JSON, default=list)
    top_features: Mapped[list] = mapped_column(JSON, default=list)
    risk_factors: Mapped[list] = mapped_column(JSON, default=list)
    model_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    historical_evidence: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CaseModel(Base):
    """Persistent record of an investigation case."""

    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="p3_medium")
    assigned_to: Mapped[str | None] = mapped_column(String(100), nullable=True)
    alert_ids: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[list] = mapped_column(JSON, default=list)
    timeline: Mapped[list] = mapped_column(JSON, default=list)
    total_risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EntityModel(Base):
    """Persistent record of a privacy-preserving entity."""

    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    privacy_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    bank_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    display_label: Mapped[str] = mapped_column(String(50), nullable=False)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    risk_level: Mapped[str] = mapped_column(String(20), default="minimal")
    alert_count: Mapped[int] = mapped_column(Integer, default=0)
    first_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )


class RelationshipModel(Base):
    """Persistent record of an entity relationship (graph edge)."""

    __tablename__ = "relationships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target_entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    relationship_type: Mapped[str] = mapped_column(String(30), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )


class SharedIntelligenceModel(Base):
    """Persistent record of shared cross-institution intelligence."""

    __tablename__ = "shared_intelligence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_bank_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    intelligence_type: Mapped[str] = mapped_column(String(30), nullable=False)
    privacy_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    risk_indicator: Mapped[float] = mapped_column(Float, default=0.0)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    related_alert_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

