"""Enterprise SLA/SLO Contract Enforcement Engine Service."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from app.domain.sla_contract import (
    PenaltyReport,
    SLAContract,
    SLOMetric,
)

logger = logging.getLogger(__name__)


class SLAContractEngine:
    """Manages tenant SLA contracts, error budget tracking, and automated credit penalty reporting."""

    def __init__(self) -> None:
        self._contracts: dict[str, SLAContract] = {}
        self._reports: list[PenaltyReport] = []

    def register_contract(
        self,
        tenant_id: str,
        uptime_target_pct: float = 99.9,
        monthly_credit_rate_pct: float = 10.0,
    ) -> SLAContract:
        """Registers a tenant enterprise SLA contract."""
        contract_id = f"sla_{uuid.uuid4().hex[:8]}"
        contract = SLAContract(
            contract_id=contract_id,
            tenant_id=tenant_id,
            uptime_target_pct=uptime_target_pct,
            monthly_credit_rate_pct=monthly_credit_rate_pct,
        )
        self._contracts[tenant_id] = contract
        logger.info(
            "Registered SLA contract %s for tenant '%s' (Uptime Target: %.2f%%)",
            contract_id,
            tenant_id,
            uptime_target_pct,
        )
        return contract

    def calculate_error_budget(
        self,
        uptime_pct: float,
        target_pct: float = 99.9,
    ) -> SLOMetric:
        """Calculates remaining error budget percentage based on target and current uptime."""
        allowed_downtime_pct = 100.0 - target_pct
        consumed_downtime_pct = max(0.0, 100.0 - uptime_pct)

        if allowed_downtime_pct > 0:
            remaining_pct = max(
                0.0,
                round(
                    ((allowed_downtime_pct - consumed_downtime_pct) / allowed_downtime_pct) * 100.0,
                    2,
                ),
            )
        else:
            remaining_pct = 0.0

        return SLOMetric(
            metric_name="UPTIME_99_9",
            target_pct=target_pct,
            current_pct=uptime_pct,
            error_budget_remaining_pct=remaining_pct,
        )

    def generate_monthly_penalty_report(
        self,
        tenant_id: str,
        month: str,
        measured_uptime_pct: float,
    ) -> PenaltyReport:
        """Evaluates SLA contract compliance and calculates automated service credits if breached."""
        contract = self._contracts.get(tenant_id)
        target_uptime = contract.uptime_target_pct if contract else 99.9
        credit_rate = contract.monthly_credit_rate_pct if contract else 10.0

        sla_breached = measured_uptime_pct < target_uptime
        credit_discount = credit_rate if sla_breached else 0.0

        report_id = f"report_sla_{uuid.uuid4().hex[:8]}"
        record = PenaltyReport(
            report_id=report_id,
            tenant_id=tenant_id,
            month=month,
            uptime_achieved_pct=measured_uptime_pct,
            sla_breached=sla_breached,
            credit_discount_pct=credit_discount,
            timestamp=datetime.now(UTC),
        )
        self._reports.append(record)

        if sla_breached:
            logger.warning(
                "SLA BREACHED for tenant '%s' in %s! Achieved Uptime: %.3f%% < Target: %.2f%%. Issued %.1f%% billing credit discount.",
                tenant_id,
                month,
                measured_uptime_pct,
                target_uptime,
                credit_discount,
            )
        else:
            logger.info(
                "SLA MET for tenant '%s' in %s (Achieved: %.3f%% >= Target: %.2f%%).",
                tenant_id,
                month,
                measured_uptime_pct,
                target_uptime,
            )

        return record

    def get_tenant_penalty_reports(self, tenant_id: str) -> list[PenaltyReport]:
        """Retrieves tenant penalty reports."""
        return [r for r in self._reports if r.tenant_id == tenant_id]
