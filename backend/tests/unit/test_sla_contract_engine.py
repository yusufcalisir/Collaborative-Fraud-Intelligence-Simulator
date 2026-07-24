# ruff: noqa: E402
"""Automated Unit Test Suite for SLA Measurement & Contract Enforcement Engine."""

from __future__ import annotations

from app.application.services.sla_contract_engine import SLAContractEngine


def test_tenant_sla_contract_registration() -> None:
    """Test tenant SLA contract registration."""
    engine = SLAContractEngine()

    contract = engine.register_contract(
        tenant_id="bank_alpha",
        uptime_target_pct=99.9,
        monthly_credit_rate_pct=10.0,
    )
    assert contract.tenant_id == "bank_alpha"
    assert contract.uptime_target_pct == 99.9
    assert contract.monthly_credit_rate_pct == 10.0


def test_error_budget_calculation() -> None:
    """Test SLO error budget remaining percentage calculation."""
    engine = SLAContractEngine()

    # 1. 100% uptime -> 100% remaining error budget
    slo_perfect = engine.calculate_error_budget(uptime_pct=100.0, target_pct=99.9)
    assert slo_perfect.error_budget_remaining_pct == 100.0

    # 2. 99.95% uptime -> 50% remaining error budget
    slo_half = engine.calculate_error_budget(uptime_pct=99.95, target_pct=99.9)
    assert slo_half.error_budget_remaining_pct == 50.0

    # 3. 99.80% uptime (breached) -> 0% remaining error budget
    slo_breached = engine.calculate_error_budget(uptime_pct=99.80, target_pct=99.9)
    assert slo_breached.error_budget_remaining_pct == 0.0


def test_monthly_penalty_report_generation_upon_sla_breach() -> None:
    """Test automated service credit calculation when monthly uptime drops below 99.9%."""
    engine = SLAContractEngine()
    tenant = "bank_beta"
    engine.register_contract(tenant_id=tenant, uptime_target_pct=99.9, monthly_credit_rate_pct=15.0)

    # 1. Compliant month (99.95%) -> No credit penalty
    rep_met = engine.generate_monthly_penalty_report(
        tenant_id=tenant,
        month="2026-06",
        measured_uptime_pct=99.95,
    )
    assert rep_met.sla_breached is False
    assert rep_met.credit_discount_pct == 0.0

    # 2. Breached month (99.50%) -> Issues 15% billing credit discount
    rep_breached = engine.generate_monthly_penalty_report(
        tenant_id=tenant,
        month="2026-07",
        measured_uptime_pct=99.50,
    )
    assert rep_breached.sla_breached is True
    assert rep_breached.credit_discount_pct == 15.0

    reports = engine.get_tenant_penalty_reports(tenant)
    assert len(reports) == 2
