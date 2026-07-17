"""Unit tests for production-grade real bank connector features.

Tests FinancialMessageParser, PSD2 router, and RabbitMQ bank connector.
"""

from __future__ import annotations

import time
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient

from app.application.services.financial_message_parser import (
    FinancialMessageParser,
    FinancialMessageParserError,
)
from app.config import Settings, get_settings
from app.domain.value_objects import ModelWeights
from app.infrastructure.connectors.rabbitmq_connector import RabbitMQBankConnector
from app.main import app

# ── Sample Data for Testing ──────────────────────────────────────────────────

PACS_008_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.08">
    <FIToFICstmrCdtTrf>
        <GrpHdr>
            <MsgId>MSG20260716-998811</MsgId>
            <CreDtTm>2026-07-16T14:30:00Z</CreDtTm>
        </GrpHdr>
        <CdtTrfTxInf>
            <PmtId>
                <EndToEndId>TX-ISO-20022-XYZ</EndToEndId>
            </PmtId>
            <IntrBkSttlmAmt Ccy="USD">15250.75</IntrBkSttlmAmt>
            <IntrBkSttlmDt>2026-07-16</IntrBkSttlmDt>
            <Dbtr>
                <Nm>Alice Smith</Nm>
                <PstlAdr>
                    <Ctry>US</Ctry>
                </PstlAdr>
            </Dbtr>
            <DbtrAcct>
                <Id>
                    <IBAN>US1234567890123456</IBAN>
                </Id>
            </DbtrAcct>
            <DbtrAgt>
                <FinInstnId>
                    <BICFI>ALICUS33XXX</BICFI>
                </FinInstnId>
            </DbtrAgt>
            <Cdtr>
                <Nm>Bob Johnson</Nm>
            </Cdtr>
            <CdtrAcct>
                <Id>
                    <IBAN>DE89370400440532013000</IBAN>
                </Id>
            </CdtrAcct>
            <CdtrAgt>
                <FinInstnId>
                    <BICFI>DBANKDEDDXXX</BICFI>
                </FinInstnId>
            </CdtrAgt>
            <RmtInf>
                <Ustrd>CONSULTING SERVICES JULY</Ustrd>
            </RmtInf>
        </CdtTrfTxInf>
    </FIToFICstmrCdtTrf>
</Document>
"""

SWIFT_MT103_MSG = """
{1:F01ALICUS33XXXX0000000000}{2:I103DBANKDEDDXXXXN}{3:{108:998811}}{4:
:20:TX-SWIFT-103-ABC
:32A:260716USD15250,75
:50K:/US1234567890123456
ALICE SMITH
123 MAPLE STREET
NEW YORK
:59:/DE89370400440532013000
BOB JOHNSON
:70:CONSULTING SERVICES JULY
:57A:DBANKDEDDXXX
-}
"""

PAIN_001_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:pain.001.001.03">
    <CstmrCdtTrfInitn>
        <GrpHdr>
            <MsgId>SEPA-PAYMENT-111</MsgId>
        </GrpHdr>
        <PmtInf>
            <Dbtr>
                <Nm>Alice Smith</Nm>
            </Dbtr>
            <DbtrAcct>
                <Id>
                    <IBAN>FR7630006000011234567890123</IBAN>
                </Id>
            </DbtrAcct>
            <CdtTrfTxInf>
                <PmtId>
                    <EndToEndId>TX-SEPA-999</EndToEndId>
                </PmtId>
                <Amt>
                    <InstdAmt Ccy="EUR">450.00</InstdAmt>
                </Amt>
                <Cdtr>
                    <Nm>Bob Johnson</Nm>
                </Cdtr>
                <CdtrAcct>
                    <Id>
                        <IBAN>DE89370400440532013000</IBAN>
                    </Id>
                </CdtrAcct>
                <RmtInf>
                    <Ustrd>DINNER REIMBURSEMENT</Ustrd>
                </RmtInf>
            </CdtTrfTxInf>
        </PmtInf>
    </CstmrCdtTrfInitn>
</Document>
"""


# ── Financial Message Parser Tests ──────────────────────────────────────────

def test_parse_iso_20022_pacs008_success() -> None:
    result = FinancialMessageParser.parse_iso_20022_pacs008(PACS_008_XML)
    assert result["message_type"] == "ISO20022_PACS008"
    assert result["transaction_id"] == "TX-ISO-20022-XYZ"
    assert result["amount"] == 15250.75
    assert result["currency"] == "USD"
    assert result["date"] == "2026-07-16"
    assert result["sender_name"] == "Alice Smith"
    assert result["sender_account"] == "US1234567890123456"
    assert result["sender_bic"] == "ALICUS33XXX"
    assert result["sender_country"] == "US"
    assert result["receiver_name"] == "Bob Johnson"
    assert result["receiver_account"] == "DE89370400440532013000"
    assert result["receiver_bic"] == "DBANKDEDDXXX"
    assert result["remittance_info"] == "CONSULTING SERVICES JULY"


def test_parse_iso_20022_pacs008_malformed() -> None:
    with pytest.raises(FinancialMessageParserError):
        FinancialMessageParser.parse_iso_20022_pacs008("<Document><Invalid></Invalid>")


def test_parse_swift_mt103_success() -> None:
    result = FinancialMessageParser.parse_swift_mt103(SWIFT_MT103_MSG)
    assert result["message_type"] == "SWIFT_MT103"
    assert result["transaction_id"] == "TX-SWIFT-103-ABC"
    assert result["amount"] == 15250.75
    assert result["currency"] == "USD"
    assert result["date"] == "2026-07-16"
    assert result["sender_name"] == "ALICE SMITH"
    assert result["sender_account"] == "US1234567890123456"
    assert result["sender_country"] == "US"
    assert result["receiver_name"] == "BOB JOHNSON"
    assert result["receiver_account"] == "DE89370400440532013000"
    assert result["receiver_bic"] == "DBANKDEDDXXX"
    assert result["remittance_info"] == "CONSULTING SERVICES JULY"


def test_parse_swift_mt103_empty() -> None:
    with pytest.raises(FinancialMessageParserError):
        FinancialMessageParser.parse_swift_mt103("")


def test_parse_sepa_credit_transfer_success() -> None:
    result = FinancialMessageParser.parse_sepa_credit_transfer(PAIN_001_XML)
    assert result["message_type"] == "SEPA_SCT"
    assert result["transaction_id"] == "TX-SEPA-999"
    assert result["amount"] == 450.00
    assert result["currency"] == "EUR"
    assert result["sender_name"] == "Alice Smith"
    assert result["sender_account"] == "FR7630006000011234567890123"
    assert result["sender_country"] == "FR"
    assert result["receiver_name"] == "Bob Johnson"
    assert result["receiver_account"] == "DE89370400440532013000"
    assert result["receiver_country"] == "DE"
    assert result["remittance_info"] == "DINNER REIMBURSEMENT"


# ── Open Banking PSD2 Router Tests ───────────────────────────────────────────

@pytest.fixture
def psd2_client() -> Generator[TestClient, None, None]:
    client = TestClient(app)
    yield client


@pytest.fixture
def valid_jwt_token() -> str:
    settings = get_settings()
    payload = {
        "sub": "tpp_client_id_123",
        "scope": "psd2:read",
        "exp": time.time() + 3600,
    }
    return jwt.encode(payload, settings.psd2_jwt_secret, algorithm="HS256")


def test_psd2_endpoints_unauthorized(psd2_client: TestClient) -> None:
    # No Auth header
    response = psd2_client.get("/api/v1/psd2/accounts", headers={"consent-id": "consent_1"})
    assert response.status_code == 401

    # Invalid Auth scheme
    response = psd2_client.get(
        "/api/v1/psd2/accounts",
        headers={"Authorization": "Basic 123", "consent-id": "consent_1"},
    )
    assert response.status_code == 401


def test_psd2_flow_success(psd2_client: TestClient, valid_jwt_token: str) -> None:
    headers = {"Authorization": f"Bearer {valid_jwt_token}"}

    # 1. Create Consent
    consent_payload = {
        "account_id": "acc_1",
        "permissions": ["read_accounts", "read_transactions"],
        "valid_until": time.time() + 3600,
    }
    resp = psd2_client.post("/api/v1/psd2/consents", json=consent_payload, headers=headers)
    assert resp.status_code == 201
    consent_data = resp.json()
    consent_id = consent_data["consent_id"]
    assert consent_id.startswith("consent_")

    # 2. Get Accounts with Consent Header
    get_headers = {**headers, "consent-id": consent_id}
    resp = psd2_client.get("/api/v1/psd2/accounts", headers=get_headers)
    assert resp.status_code == 200
    accounts = resp.json()
    assert len(accounts) == 1
    assert accounts[0]["account_id"] == "acc_1"
    assert accounts[0]["iban"] == "DE89370400440532013000"

    # 3. Get Transactions
    resp = psd2_client.get("/api/v1/psd2/accounts/acc_1/transactions", headers=get_headers)
    assert resp.status_code == 200
    txs = resp.json()
    assert len(txs) == 2
    assert txs[0]["transaction_id"] == "tx_psd2_1001"


def test_psd2_flow_forbidden_no_consent(psd2_client: TestClient, valid_jwt_token: str) -> None:
    headers = {"Authorization": f"Bearer {valid_jwt_token}", "consent-id": "nonexistent_consent"}
    resp = psd2_client.get("/api/v1/psd2/accounts", headers=headers)
    assert resp.status_code == 403


# ── RabbitMQ Connector Tests ─────────────────────────────────────────────────

def test_rabbitmq_fallback_to_mock() -> None:
    # Setup mock fallback connector
    mock_fallback = MagicMock()
    mock_fallback.initialize.return_value = {"status": "initialized", "num_samples": 100}

    # Initialize connector targeting an invalid rabbitmq address (ensures connection fails and falls back)
    connector = RabbitMQBankConnector(
        host="invalid-host-unreachable",
        port=5672,
        fallback_connector=mock_fallback,
    )

    res = connector.initialize(bank_id="bank-a", num_transactions=100, seed=42)
    assert res["status"] == "initialized"
    mock_fallback.initialize.assert_called_once_with(bank_id="bank-a", num_transactions=100, seed=42)


@patch("pika.BlockingConnection")
def test_rabbitmq_success_flow(mock_blocking_conn: MagicMock) -> None:
    # Setup mock connection and channel
    mock_conn = MagicMock()
    mock_channel = MagicMock()
    mock_blocking_conn.return_value = mock_conn
    mock_conn.channel.return_value = mock_channel

    mock_channel.queue_declare.return_value = MagicMock()

    # Simulate immediate response on channel process_data_events
    def fake_process_data_events(time_limit: float = 0) -> None:
        # Call the registered consumer callback
        args, kwargs = mock_channel.basic_consume.call_args
        callback = kwargs.get("on_message_callback") or args[1]

        # Prepare dummy envelope & props
        method_frame = MagicMock()
        method_frame.delivery_tag = 1
        properties = MagicMock()
        properties.correlation_id = "test_corr_id"

        response_bytes = b'{"status": "success", "loss": 0.42}'
        callback(mock_channel, method_frame, properties, response_bytes)

    mock_conn.process_data_events.side_effect = fake_process_data_events

    connector = RabbitMQBankConnector(
        host="localhost",
        port=5672,
    )

    weights = ModelWeights(layer_shapes=[(2, 2)], flat_weights=[0.1, 0.2, 0.3, 0.4])

    res = connector.train(
        bank_id="bank-a",
        weights=weights,
        learning_rate=0.01,
        batch_size=32,
        epochs=1,
        enable_dp=False,
        dp_epsilon=1.0,
        dp_delta=1e-5,
        dp_max_grad_norm=1.0,
        correlation_id="test_corr_id",
    )

    assert res["status"] == "success"
    assert res["loss"] == 0.42

    # Assert pika publishing calls
    mock_channel.basic_publish.assert_called_once()
