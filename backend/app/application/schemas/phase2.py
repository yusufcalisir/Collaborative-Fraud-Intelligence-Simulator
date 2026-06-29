"""Pydantic schemas for Phase 2 API endpoints.

Request/response models for alerts, cases, entities, graph,
scenarios, and intelligence.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# ── Alerts ────────────────────────────────────


class AlertResponse(BaseModel):
    id: str
    bank_id: str
    transaction_id: str
    risk_score: float
    severity: str
    status: str
    reason_codes: list[str]
    confidence: float
    involved_entity_ids: list[str]
    created_at: str
    top_features: list[dict] = []
    risk_factors: list[str] = []
    model_confidence: float = 0.0


class ExplainabilityResponse(BaseModel):
    alert_id: str
    top_features: list[dict]
    risk_factors: list[str]
    historical_evidence: list[str]
    model_confidence: float
    risk_score_breakdown: list[dict] = []
    explanation_text: str = ""


class IntelligenceStatsResponse(BaseModel):
    total_items: int
    items_by_type: dict[str, int]
    items_by_bank: dict[str, int]
    avg_risk_indicator: float


class SharedIntelligenceResponse(BaseModel):
    id: str
    source_bank_id: str
    intelligence_type: str
    privacy_hash: str
    risk_indicator: float
    description: str
    entity_type: str | None = None
    related_alert_count: int = 0
    created_at: str


# ── Cases ─────────────────────────────────────


class CaseCreateRequest(BaseModel):
    title: str
    priority: str = "p3_medium"
    alert_ids: list[str] = []


class CaseNoteRequest(BaseModel):
    author: str = "analyst"
    content: str


class CaseStatusRequest(BaseModel):
    status: str
    actor: str = "analyst"


class CaseLinkAlertRequest(BaseModel):
    alert_id: str


class CaseNoteResponse(BaseModel):
    id: str
    case_id: str
    author: str
    content: str
    created_at: str


class CaseEventResponse(BaseModel):
    event_type: str
    description: str
    actor: str
    timestamp: str
    metadata: dict = {}


class CaseResponse(BaseModel):
    id: str
    title: str
    status: str
    priority: str
    assigned_to: str | None = None
    alert_ids: list[str]
    notes: list[CaseNoteResponse] = []
    timeline: list[CaseEventResponse] = []
    created_at: str
    updated_at: str | None = None
    closed_at: str | None = None
    total_risk_score: float = 0.0
    duration_hours: float | None = None
    is_open: bool = True


class CaseSummaryResponse(BaseModel):
    id: str
    title: str
    status: str
    priority: str
    assigned_to: str | None = None
    alert_count: int
    created_at: str
    is_open: bool = True


# ── Entities ──────────────────────────────────


class EntityResponse(BaseModel):
    id: str
    entity_type: str
    privacy_id: str
    bank_id: str
    display_label: str
    attributes: dict = {}
    risk_level: str
    alert_count: int = 0
    first_seen: str
    last_seen: str


class EntityProfileResponse(BaseModel):
    entity_id: str
    entity_type: str
    privacy_id: str
    display_label: str
    bank_id: str
    risk_level: str
    alert_count: int
    relationship_count: int
    cross_institution_count: int
    banks_present: list[str]
    first_seen: str
    last_seen: str
    attributes: dict = {}


class EntityResolveRequest(BaseModel):
    privacy_hash: str


class CrossInstitutionMatchResponse(BaseModel):
    privacy_hash: str
    entity_type: str
    bank_a_entity_id: str
    bank_b_entity_id: str
    bank_a_risk: str
    bank_b_risk: str


# ── Graph ─────────────────────────────────────


class GraphNodeResponse(BaseModel):
    id: str
    type: str = "default"
    position: dict
    data: dict
    style: dict = {}


class GraphEdgeResponse(BaseModel):
    id: str
    source: str
    target: str
    label: str = ""
    type: str = "smoothstep"
    animated: bool = False
    style: dict = {}
    data: dict = {}


class GraphResponse(BaseModel):
    nodes: list[dict]
    edges: list[dict]
    clusters: list[list[str]] = []
    center_entity_id: str = ""
    depth: int = 2


class GraphStatsResponse(BaseModel):
    total_nodes: int
    total_edges: int
    nodes_by_type: dict[str, int]
    nodes_by_risk: dict[str, int]
    cluster_count: int


# ── Scenarios ─────────────────────────────────


class ScenarioInfoResponse(BaseModel):
    type: str
    name: str
    description: str
    banks_involved: list[str]
    estimated_events: int
    estimated_duration_seconds: float


class ScenarioStartRequest(BaseModel):
    scenario_type: str
    speed_multiplier: float = Field(default=1.0, ge=0.1, le=10.0)


class ScenarioStartResponse(BaseModel):
    scenario_id: str
    scenario_type: str
    name: str
    total_events: int
    status: str = "running"


class ScenarioStatusResponse(BaseModel):
    scenario_id: str
    status: str
    total_events: int
    delivered_events: int
    speed_multiplier: float
    started_at: str


# ── Risk ──────────────────────────────────────


class RiskWeightsResponse(BaseModel):
    ml_prediction: float
    velocity_rules: float
    merchant_reputation: float
    country_risk: float
    device_anomaly: float
    customer_history: float
    previous_alerts: float
    chargeback_history: float
    behavior_anomaly: float


class RiskWeightsUpdateRequest(BaseModel):
    ml_prediction: float = 0.25
    velocity_rules: float = 0.15
    merchant_reputation: float = 0.10
    country_risk: float = 0.10
    device_anomaly: float = 0.08
    customer_history: float = 0.10
    previous_alerts: float = 0.08
    chargeback_history: float = 0.07
    behavior_anomaly: float = 0.07


# ── Investigation Dashboard ──────────────────


class DashboardStatsResponse(BaseModel):
    total_alerts: int
    critical_alerts: int
    open_cases: int
    total_entities: int
    shared_intelligence_items: int
    cross_institution_matches: int
    active_scenarios: int
    graph_clusters: int
