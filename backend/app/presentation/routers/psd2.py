"""Open Banking PSD2 (XS2A) API Router.

Exposes standardized endpoints for third-party AISPs to retrieve account list,
transaction histories, and manage consent verification with JWT auth.
"""

from __future__ import annotations

import time
from typing import Any

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.config import get_settings

router = APIRouter(prefix="/api/v1/psd2", tags=["PSD2 Open Banking"])

# Simple in-memory consent store: {consent_id: consent_data}
_consents: dict[str, dict[str, Any]] = {}


class ConsentRequest(BaseModel):
    account_id: str
    permissions: list[str] = Field(default_factory=lambda: ["read_accounts", "read_transactions"])
    valid_until: float = Field(description="Epoch timestamp representing valid until date")


class ConsentResponse(BaseModel):
    consent_id: str
    status: str
    account_id: str
    permissions: list[str]
    valid_until: float


class AccountResponse(BaseModel):
    account_id: str
    iban: str
    currency: str
    balance: float
    bank_name: str


class TransactionResponse(BaseModel):
    transaction_id: str
    amount: float
    currency: str
    booking_date: str
    debtor_name: str
    creditor_name: str
    remittance_info: str


def get_jwt_subject(authorization: str | None = Header(None)) -> dict[str, Any]:
    """Dependency verifying Bearer JWT token."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing.",
        )
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme. Bearer required.",
        )
    token = authorization.split(" ")[1]
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.psd2_jwt_secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature or claims.",
        ) from exc


@router.post("/consents", response_model=ConsentResponse, status_code=status.HTTP_201_CREATED)
async def create_consent(
    payload: ConsentRequest,
    token_payload: dict[str, Any] = Depends(get_jwt_subject),
) -> ConsentResponse:
    """Create a new PSD2 consent for a third-party provider."""
    consent_id = f"consent_{int(time.time())}_{payload.account_id}"
    consent_data = {
        "consent_id": consent_id,
        "status": "valid",
        "account_id": payload.account_id,
        "permissions": payload.permissions,
        "valid_until": payload.valid_until,
        "client_id": token_payload.get("sub", "unknown_client"),
    }
    _consents[consent_id] = consent_data
    return ConsentResponse(**consent_data)


@router.get("/accounts", response_model=list[AccountResponse])
async def list_consented_accounts(
    consent_id: str = Header(...),
    token_payload: dict[str, Any] = Depends(get_jwt_subject),
) -> list[AccountResponse]:
    """Retrieve consented customer accounts using a valid consent header."""
    consent = _consents.get(consent_id)
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Consent not found.",
        )
    if consent["status"] != "valid" or consent["valid_until"] < time.time():
        consent["status"] = "expired"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Consent has expired or is invalid.",
        )
    # Validate permissions
    if "read_accounts" not in consent["permissions"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient consent permissions for reading accounts.",
        )

    # Return mock consented account matching the ID
    return [
        AccountResponse(
            account_id=consent["account_id"],
            iban="DE89370400440532013000"
            if consent["account_id"] == "acc_1"
            else "FR7630006000011234567890123",
            currency="EUR",
            balance=42000.50,
            bank_name="Nexus Digital" if consent["account_id"] == "acc_1" else "Meridian National",
        )
    ]


@router.get("/accounts/{account_id}/transactions", response_model=list[TransactionResponse])
async def list_account_transactions(
    account_id: str,
    consent_id: str = Header(...),
    token_payload: dict[str, Any] = Depends(get_jwt_subject),
) -> list[TransactionResponse]:
    """Retrieve transaction history for a consented account under PSD2 specifications."""
    consent = _consents.get(consent_id)
    if not consent or consent["account_id"] != account_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Consent not matching target account id.",
        )
    if consent["status"] != "valid" or consent["valid_until"] < time.time():
        consent["status"] = "expired"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Consent has expired or is invalid.",
        )
    # Validate permissions
    if "read_transactions" not in consent["permissions"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient consent permissions for reading transactions.",
        )

    # Return normalized mock transactions
    return [
        TransactionResponse(
            transaction_id="tx_psd2_1001",
            amount=250.00,
            currency="EUR",
            booking_date="2026-07-16T12:00:00Z",
            debtor_name="John Doe",
            creditor_name="Crypto Exchange Ltd",
            remittance_info="SEPA INSTANT TRANSFER DEB-1",
        ),
        TransactionResponse(
            transaction_id="tx_psd2_1002",
            amount=1500.00,
            currency="EUR",
            booking_date="2026-07-16T15:30:00Z",
            debtor_name="John Doe",
            creditor_name="Luxury Watch Retailer",
            remittance_info="GIFT",
        ),
    ]
