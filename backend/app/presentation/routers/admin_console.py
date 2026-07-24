"""Admin Web Console Router servicing commercial dashboards."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from pydantic import BaseModel

from app.domain.web_console import (
    ConsoleMetricSummary,
    ConsoleUserRole,
    RoleViewConfig,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/admin/dashboard", tags=["Admin Web Console"])


class DashboardSummaryResponse(BaseModel):
    """Schema for platform summary metrics."""

    active_bank_nodes_count: int
    federated_rounds_completed: int
    global_model_auc: float
    total_cases_opened: int
    sla_compliance_pct: float


class RoleConfigResponse(BaseModel):
    """Schema for role-based view configuration."""

    role: ConsoleUserRole
    visible_widgets: list[str]
    permissions: list[str]
    theme: str


ROLE_CONFIG_MAP: dict[ConsoleUserRole, RoleViewConfig] = {
    ConsoleUserRole.EXECUTIVE: RoleViewConfig(
        role=ConsoleUserRole.EXECUTIVE,
        visible_widgets=["roi_chart", "total_fraud_prevented", "sla_summary"],
        permissions=["read_executive_reports"],
    ),
    ConsoleUserRole.COMPLIANCE_OFFICER: RoleViewConfig(
        role=ConsoleUserRole.COMPLIANCE_OFFICER,
        visible_widgets=["privacy_budget_gauge", "sar_filings", "audit_logs", "gdpr_erasure"],
        permissions=["sign_off_compliance", "file_sar", "audit_view"],
    ),
    ConsoleUserRole.ML_ENGINEER: RoleViewConfig(
        role=ConsoleUserRole.ML_ENGINEER,
        visible_widgets=[
            "drift_monitor",
            "canary_eval",
            "model_lifecycle_machine",
            "retraining_jobs",
        ],
        permissions=["promote_model", "trigger_retraining", "view_ml_metrics"],
    ),
    ConsoleUserRole.FRAUD_INVESTIGATOR: RoleViewConfig(
        role=ConsoleUserRole.FRAUD_INVESTIGATOR,
        visible_widgets=["case_workbench", "entity_graph", "shap_explainability", "alert_feed"],
        permissions=["assign_case", "escalate_case", "resolve_case"],
    ),
}


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary() -> DashboardSummaryResponse:
    """Returns unified high-level system performance metrics for web console."""
    summary = ConsoleMetricSummary()
    return DashboardSummaryResponse(
        active_bank_nodes_count=summary.active_bank_nodes_count,
        federated_rounds_completed=summary.federated_rounds_completed,
        global_model_auc=summary.global_model_auc,
        total_cases_opened=summary.total_cases_opened,
        sla_compliance_pct=summary.sla_compliance_pct,
    )


@router.get("/role-config", response_model=RoleConfigResponse)
def get_role_configuration(
    role: ConsoleUserRole = ConsoleUserRole.EXECUTIVE,
) -> RoleConfigResponse:
    """Returns widget visibility and UI configuration tailored per enterprise user role."""
    config = ROLE_CONFIG_MAP.get(role, ROLE_CONFIG_MAP[ConsoleUserRole.EXECUTIVE])
    return RoleConfigResponse(
        role=config.role,
        visible_widgets=config.visible_widgets,
        permissions=config.permissions,
        theme=config.theme,
    )
