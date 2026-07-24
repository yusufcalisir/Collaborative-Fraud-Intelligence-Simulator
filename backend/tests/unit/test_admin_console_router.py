# ruff: noqa: E402
"""Automated Unit Test Suite for Commercial Admin Web Console Router."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.presentation.routers.admin_console import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def test_dashboard_summary_endpoint() -> None:
    """Test GET /v1/admin/dashboard/summary endpoint for web console metrics."""
    response = client.get("/v1/admin/dashboard/summary")
    assert response.status_code == 200

    data = response.json()
    assert data["active_bank_nodes_count"] >= 3
    assert data["federated_rounds_completed"] >= 20
    assert data["global_model_auc"] > 0.80
    assert data["sla_compliance_pct"] >= 99.0


def test_role_configuration_filtering() -> None:
    """Test GET /v1/admin/dashboard/role-config widget and permission filtering for all personas."""
    roles = ["EXECUTIVE", "COMPLIANCE_OFFICER", "ML_ENGINEER", "FRAUD_INVESTIGATOR"]

    for r in roles:
        response = client.get("/v1/admin/dashboard/role-config", params={"role": r})
        assert response.status_code == 200

        data = response.json()
        assert data["role"] == r
        assert len(data["visible_widgets"]) >= 1
        assert len(data["permissions"]) >= 1
        assert "theme" in data

    # Check ML_ENGINEER specific widget
    res_ml = client.get("/v1/admin/dashboard/role-config", params={"role": "ML_ENGINEER"})
    widgets_ml = res_ml.json()["visible_widgets"]
    assert "drift_monitor" in widgets_ml

    # Check FRAUD_INVESTIGATOR specific widget
    res_inv = client.get("/v1/admin/dashboard/role-config", params={"role": "FRAUD_INVESTIGATOR"})
    widgets_inv = res_inv.json()["visible_widgets"]
    assert "case_workbench" in widgets_inv
