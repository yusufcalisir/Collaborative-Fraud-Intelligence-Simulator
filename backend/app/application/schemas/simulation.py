"""Pydantic schemas for simulation API endpoints."""

from __future__ import annotations

from datetime import datetime  # noqa: TC003

from pydantic import BaseModel, Field

from app.domain.enums import PrivacyMechanism, SimulationStatus


class SimulationConfigRequest(BaseModel):
    """Request body for creating a new simulation."""

    num_rounds: int = Field(default=10, ge=1, le=100, description="Number of federated rounds")
    local_epochs: int = Field(default=3, ge=1, le=20, description="Local training epochs per round")
    learning_rate: float = Field(default=0.001, gt=0, le=1.0)
    batch_size: int = Field(default=64, ge=8, le=512)
    min_clients_per_round: int = Field(default=2, ge=1, le=3)

    # Failure simulation
    enable_latency_simulation: bool = False
    latency_min_ms: int = Field(default=50, ge=0, le=5000)
    latency_max_ms: int = Field(default=500, ge=0, le=5000)
    enable_dropout_simulation: bool = False
    dropout_probability: float = Field(default=0.2, ge=0, le=0.8)
    enable_reconnect_simulation: bool = True

    # Privacy
    privacy_mechanism: PrivacyMechanism = PrivacyMechanism.NONE
    dp_epsilon: float = Field(default=1.0, gt=0)
    dp_delta: float = Field(default=1e-5, gt=0)
    dp_max_grad_norm: float = Field(default=1.0, gt=0)
    dp_mode: str = Field(
        default="post_hoc",
        description="DP implementation mode: post_hoc (clip+noise after training) or opacus (per-sample gradient privacy)",
    )

    # Data volume
    bank_a_transactions: int = Field(default=50000, ge=1000, le=200000)
    bank_b_transactions: int = Field(default=30000, ge=1000, le=200000)
    bank_c_transactions: int = Field(default=20000, ge=1000, le=200000)

    # Aggregation strategy
    aggregation_method: str = Field(
        default="fed_avg_weighted",
        description="Aggregation algorithm: fed_avg_weighted, fed_avg, krum, coordinate_wise_median",
    )

    # Adversarial / poisoning simulation
    enable_poisoning_simulation: bool = False
    poisoning_bank_id: str = Field(default="bank_c", description="Bank to act as malicious client")
    poisoning_scale: float = Field(
        default=5.0, ge=1.0, le=20.0, description="Poisoning noise magnitude"
    )


class SimulationSummaryResponse(BaseModel):
    """Abbreviated simulation info for list views."""

    id: str
    status: SimulationStatus
    current_round: int
    total_rounds: int
    progress_pct: float
    created_at: datetime
    completed_at: datetime | None = None
    duration_seconds: float | None = None


class SimulationDetailResponse(BaseModel):
    """Full simulation details including per-bank metrics."""

    id: str
    status: SimulationStatus
    config: SimulationConfigRequest
    current_round: int
    total_rounds: int
    progress_pct: float
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    error_message: str | None = None
    banks: list[BankResponse] = []
    rounds: list[RoundResponse] = []


class SimulationCreateResponse(BaseModel):
    """Response after initiating a simulation."""

    id: str
    status: SimulationStatus
    message: str


# Forward reference resolution
class BankResponse(BaseModel):
    """Bank details within a simulation response."""

    id: str
    name: str
    tier: str
    fraud_ratio: float
    num_transactions: int
    status: str
    local_metrics: MetricsResponse | None = None
    federated_metrics: MetricsResponse | None = None
    improvement: dict[str, float] | None = None
    data_profile: DataProfileResponse | None = None


class MetricsResponse(BaseModel):
    """Evaluation metrics for a model."""

    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auc_roc: float
    loss: float
    confusion_matrix: list[list[int]]
    roc_fpr: list[float]
    roc_tpr: list[float]
    roc_thresholds: list[float]
    feature_importance: dict[str, float] = {}


class DataProfileResponse(BaseModel):
    """Statistical profile of a bank's dataset."""

    bank_name: str
    num_transactions: int
    fraud_ratio: float
    mean_transaction_amount: float
    std_transaction_amount: float
    top_merchant_categories: list[str]
    top_countries: list[str]
    mean_account_age_days: float
    mean_velocity: float


class RoundResponse(BaseModel):
    """Details of a single federated training round."""

    round_number: int
    global_loss: float
    participating_banks: list[str]
    dropped_banks: list[str]
    per_bank_loss: dict[str, float]
    per_bank_samples: dict[str, int]
    aggregation_time_ms: float
    round_duration_ms: float
    privacy_budget_spent: float = 0.0


class ComparisonResponse(BaseModel):
    """Side-by-side local vs federated comparison across all banks."""

    simulation_id: str
    banks: list[BankComparisonResponse]
    aggregate_improvement: dict[str, float]


class BankComparisonResponse(BaseModel):
    """Per-bank local vs federated comparison."""

    bank_id: str
    bank_name: str
    local_metrics: MetricsResponse
    federated_metrics: MetricsResponse
    improvement: dict[str, float]


# Rebuild models to resolve forward references
SimulationDetailResponse.model_rebuild()
