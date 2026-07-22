"""Unit tests for Web3 & CBDC Smart Contract Incentive Settlement."""

import pytest
from app.infrastructure.security.smart_contract_driver import (
    SmartContractSettlementDriver,
)


def test_smart_contract_driver_singleton():
    driver1 = SmartContractSettlementDriver.get_instance()
    driver2 = SmartContractSettlementDriver.get_instance()
    assert driver1 is driver2
    assert driver1.contract_address == "0x71C7656EC7ab88b098defB751B7401B5f6d8976F"


def test_settle_incentives_success():
    driver = SmartContractSettlementDriver()
    contributions = {"Bank A": 0.45, "Bank B": 0.35, "Bank C": 0.20}
    quarantine_statuses = {"Bank A": False, "Bank B": False, "Bank C": False}
    audit_hash = "a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890"

    receipt = driver.settle_incentives(
        epoch_id="test_sim_001",
        contributions=contributions,
        quarantine_statuses=quarantine_statuses,
        audit_proof_hash=audit_hash,
        total_pool_usd=100000.0,
        currency="wCBDC",
    )

    assert receipt["status"] == "SUCCESS"
    assert receipt["transaction_hash"].startswith("0x")
    assert receipt["block_number"] > 5000000
    assert receipt["total_distributed_usd"] == 100000.0
    assert receipt["currency"] == "wCBDC"
    assert len(receipt["payouts"]) == 3

    # Verify Bank A share: 0.45 / 1.0 = 45% = $45,000
    bank_a = next(p for p in receipt["payouts"] if p["bank_name"] == "Bank A")
    assert bank_a["payout_usd"] == 45000.0
    assert bank_a["share_percent"] == 45.0
    assert bank_a["status"] == "DISTRIBUTED"


def test_settle_incentives_with_quarantined_node():
    driver = SmartContractSettlementDriver()
    contributions = {"Bank A": 0.50, "Bank B": 0.50, "Bank C": -0.20}
    quarantine_statuses = {"Bank A": False, "Bank B": False, "Bank C": True}
    audit_hash = "f6e5d4c3b2a10987f6e5d4c3b2a10987f6e5d4c3b2a10987f6e5d4c3b2a10987"

    receipt = driver.settle_incentives(
        epoch_id="test_sim_002",
        contributions=contributions,
        quarantine_statuses=quarantine_statuses,
        audit_proof_hash=audit_hash,
        total_pool_usd=100000.0,
        currency="USDC",
    )

    assert receipt["status"] == "SUCCESS"
    bank_c = next(p for p in receipt["payouts"] if p["bank_name"] == "Bank C")
    assert bank_c["is_quarantined"] is True
    assert bank_c["payout_usd"] == 0.0
    assert bank_c["status"] == "BLOCKED_QUARANTINE"


def test_get_contract_info():
    driver = SmartContractSettlementDriver()
    info = driver.get_contract_info()
    assert info["contract_address"] == "0x71C7656EC7ab88b098defB751B7401B5f6d8976F"
    assert info["chain_id"] == 11155111
    assert "abi" in info
    assert "wCBDC" in info["supported_currencies"]
