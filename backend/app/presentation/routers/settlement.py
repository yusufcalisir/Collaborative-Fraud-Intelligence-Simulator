"""Web3 & CBDC Smart Contract Incentive Settlement API Endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.infrastructure.security.smart_contract_driver import (
    SmartContractSettlementDriver,
)

router = APIRouter(prefix="/api/v1/settlement", tags=["settlement"])


class SettlementTriggerRequest(BaseModel):
    epoch_id: str
    contributions: dict[str, float]
    quarantine_statuses: dict[str, bool] = Field(default_factory=dict)
    audit_proof_hash: str
    total_pool_usd: float = 100000.0
    currency: str = "wCBDC"


@router.get("/contract-info")
async def get_contract_info() -> dict[str, Any]:
    """Returns metadata and ABI for the deployed Consortium Incentive Settlement Smart Contract."""
    driver = SmartContractSettlementDriver.get_instance()
    return driver.get_contract_info()


@router.get("/history")
async def get_settlement_history() -> list[dict[str, Any]]:
    """Returns the log of executed on-chain Web3 / CBDC settlement receipts."""
    driver = SmartContractSettlementDriver.get_instance()
    return driver.get_settlement_history()


@router.post("/trigger")
async def trigger_settlement(payload: SettlementTriggerRequest) -> dict[str, Any]:
    """Manually triggers smart contract incentive settlement for a simulation epoch."""
    try:
        driver = SmartContractSettlementDriver.get_instance()
        receipt = driver.settle_incentives(
            epoch_id=payload.epoch_id,
            contributions=payload.contributions,
            quarantine_statuses=payload.quarantine_statuses,
            audit_proof_hash=payload.audit_proof_hash,
            total_pool_usd=payload.total_pool_usd,
            currency=payload.currency,
        )
        return receipt
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Settlement execution failed: {exc}") from exc
