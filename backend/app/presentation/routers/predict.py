"""Predict and serving API router.

Evaluates transaction payloads in real-time using the active global model,
computes risk scores, generates explainability reports, and triggers alerts.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

import torch
from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from app.application.services.alert_service import AlertIntelligenceService
from app.application.services.explainability_service import ExplainabilityService
from app.application.services.model_registry import ModelRegistry
from app.application.services.model_service import ModelService
from app.application.services.risk_engine import RiskScoringEngine
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["prediction"])

# Singleton instances (matching backend router architectures)
_settings = get_settings()
_model_service = ModelService(_settings)
_registry = ModelRegistry()
_risk_engine = RiskScoringEngine()
_alert_service = AlertIntelligenceService()
_explainability_service = ExplainabilityService()

# Global reference bounds for min-max scaling of single transactions
REFERENCE_BOUNDS = {
    "transaction_amount": (0.0, 5000.0),
    "merchant_category": (0.0, 19.0),
    "country_code": (0.0, 19.0),
    "device_type": (0.0, 4.0),
    "velocity": (0.0, 30.0),
    "hour_of_day": (0.0, 23.0),
    "merchant_risk_score": (0.0, 1.0),
    "customer_history_score": (0.0, 1.0),
    "chargeback_count": (0.0, 10.0),
    "account_age_days": (0.0, 1000.0),
}


class TransactionPredictRequest(BaseModel):
    transaction_amount: float = Field(..., ge=0.0, description="Amount of the transaction")
    merchant_category: str = Field(
        "grocery", description="Merchant category name (e.g. crypto, grocery, travel)"
    )
    country_code: str = Field("US", description="Originating ISO country code (e.g. US, NG, TR)")
    device_type: str = Field(
        "web_browser", description="Type of device (e.g. web_browser, mobile_app)"
    )
    velocity: float = Field(1.0, ge=0.0, description="Transaction velocity (txns/hr)")
    hour_of_day: int = Field(12, ge=0, le=23, description="Hour of the transaction")
    merchant_risk_score: float = Field(
        0.05, ge=0.0, le=1.0, description="Historical fraud rate of the merchant"
    )
    customer_history_score: float = Field(
        0.95, ge=0.0, le=1.0, description="Trustworthiness score of the customer"
    )
    chargeback_count: int = Field(0, ge=0, description="Customer chargeback count")
    account_age_days: int = Field(365, ge=0, description="Age of the customer account in days")
    bank_id: str | None = Field(
        None, description="Optional bank identifier. Defaults to gateway ID."
    )
    simulation_id: str | None = Field(
        None, description="Optional simulation run ID to resolve versioned models."
    )


class SignalBreakdown(BaseModel):
    signal_name: str
    weight: float
    raw_value: float
    normalized_score: float
    explanation: str


class AlertDetails(BaseModel):
    alert_id: str
    severity: str
    status: str
    reason_codes: list[str]
    explanation: str
    top_features: list[dict[str, Any]]
    risk_factors: list[str]


class TransactionPredictResponse(BaseModel):
    fraud_probability: float
    risk_score: float
    is_fraud_suspected: bool
    risk_level: str
    breakdown: list[SignalBreakdown]
    alert_details: AlertDetails | None = None


def preprocess_transaction(txn: dict[str, Any]) -> torch.Tensor:
    """Preprocess, ordinal-encode, and min-max scale a single transaction payload."""
    from app.application.services.data_generator import (
        COUNTRIES,
        DEVICES,
        FEATURE_NAMES,
        MERCHANT_CATEGORIES,
    )

    vals = []
    for name in FEATURE_NAMES:
        val = txn.get(name)
        if val is None:
            # Defaults matching data generator logic
            if name == "country_code":
                val = "US"
            elif name == "merchant_category":
                val = "grocery"
            elif name == "device_type":
                val = "web_browser"
            else:
                val = 0.0

        # Encode categorical variables using constant list indexes
        if name == "merchant_category":
            val = float(MERCHANT_CATEGORIES.index(val) if val in MERCHANT_CATEGORIES else 0)
        elif name == "country_code":
            val = float(COUNTRIES.index(val) if val in COUNTRIES else 0)
        elif name == "device_type":
            val = float(DEVICES.index(val) if val in DEVICES else 0)
        else:
            val = float(val)

        # Scale with pre-defined dataset reference bounds
        c_min, c_max = REFERENCE_BOUNDS.get(name, (0.0, 1.0))
        if c_max > c_min:
            val_norm = (val - c_min) / (c_max - c_min)
            val_norm = max(0.0, min(1.0, val_norm))  # clip to [0, 1]
        else:
            val_norm = 0.0
        vals.append(val_norm)

    return torch.FloatTensor([vals])


@router.post("/predict", response_model=TransactionPredictResponse)
async def predict_transaction(
    payload: TransactionPredictRequest,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
) -> TransactionPredictResponse:
    """Evaluate a transaction in real-time.

    Loads the currently active global model (or versioned model of a simulation),
    evaluates fraud probability, computes composite risk score, and
    generates alerts if fraud is suspected.
    """
    # 1. Resolve active model weights state dict
    state_dict = None
    if payload.simulation_id:
        # Load from registry version
        active_entry = _registry.get_active_version(payload.simulation_id)
        if not active_entry:
            versions = _registry.list_versions(payload.simulation_id)
            if versions:
                active_entry = max(versions, key=lambda x: x["version"])

        if not active_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No trained models found for simulation ID: {payload.simulation_id}",
            )
        try:
            state_dict = _registry.load_version(payload.simulation_id, active_entry["version"])
        except Exception as e:
            logger.error(
                "Failed to load versioned model for simulation %s: %s", payload.simulation_id, e
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error loading registered model version: {e}",
            )
    else:
        # Load default serving model path
        global_path = os.path.join(_registry.storage_dir, "global_model.pt")
        if not os.path.exists(global_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Active global model not found. Run a federated training run to generate one.",
            )
        try:
            state_dict = torch.load(global_path, map_location="cpu")
        except Exception as e:
            logger.error("Failed to load serving model: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error loading served model file: {e}",
            )

    # 2. Determine DP model compatibility dynamically based on layer parameter keys
    dp_compatible = True
    for key in state_dict:
        if "running_mean" in key or "running_var" in key:
            dp_compatible = False
            break

    # 3. Instantiate model and perform forward pass
    try:
        model = _model_service.create_model(dp_compatible=dp_compatible)
        model.load_state_dict(state_dict)
        model.eval()

        txn_dict = payload.model_dump()
        input_tensor = preprocess_transaction(txn_dict).to(_model_service.device)

        with torch.no_grad():
            fraud_prob = float(model(input_tensor).item())
    except Exception as e:
        logger.error("Inference execution failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference pipeline execution error: {e}",
        )

    # 4. Compute composite risk score
    bank_id = payload.bank_id or "serving_client"
    # Compute one-way hash of transaction for scoring entity resolution checks
    txn_id = str(uuid.uuid4())
    entity_hash = f"serving:{bank_id}:{txn_id[:8]}"

    # Register historical signals context dynamically for the entity hash
    if payload.chargeback_count > 0:
        _risk_engine.register_chargeback(entity_hash, min(1.0, payload.chargeback_count / 10.0))
        for _ in range(min(5, payload.chargeback_count)):
            _risk_engine.register_alert(entity_hash)
    _risk_engine.register_baseline(entity_hash, {"mean_amount": 100.0, "std_amount": 50.0})

    risk_score_obj = _risk_engine.score_transaction(
        transaction=txn_dict,
        ml_prediction=fraud_prob,
        entity_hash=entity_hash,
    )

    score = risk_score_obj.score
    is_fraud_suspected = score >= 600.0
    risk_level = (
        "CRITICAL"
        if score >= 800.0
        else ("HIGH" if score >= 600.0 else ("MEDIUM" if score >= 300.0 else "LOW"))
    )

    # 5. Alert Triggering and Collaboration
    alert_details = None
    if is_fraud_suspected:
        try:
            # Map input parameters into AlertIntelligence txn dictionary format
            features_dict = {
                "transaction_id": txn_id,
                "velocity": payload.velocity,
                "merchant_category": payload.merchant_category,
                "country_code": payload.country_code,
                "device_type": payload.device_type,
                "transaction_amount": payload.transaction_amount,
                "merchant_risk_score": payload.merchant_risk_score,
                "customer_history_score": payload.customer_history_score,
                "chargeback_count": payload.chargeback_count,
                "account_age_days": payload.account_age_days,
            }

            # Generate and persist the alert in Redis
            alerts = _alert_service.generate_alerts(
                bank_id=bank_id,
                transactions=[features_dict],
                predictions=[score / 1000.0],
                threshold=0.01,  # Set low threshold to guarantee alert creation
            )

            if alerts:
                active_alert = alerts[0]
                # Publish anonymized indicator to the shared intelligence layer
                _alert_service.publish_intelligence(active_alert)

                # Generate the SHAP attribution explanation report
                explanation_report = _explainability_service.explain_alert(
                    active_alert,
                    risk_signals=risk_score_obj.signals,
                )

                alert_details = AlertDetails(
                    alert_id=active_alert.id,
                    severity=active_alert.severity.value,
                    status=active_alert.status.value,
                    reason_codes=active_alert.reason_codes,
                    explanation=explanation_report.explanation_text,
                    top_features=active_alert.top_features,
                    risk_factors=active_alert.risk_factors,
                )
        except Exception as e:
            logger.warning("Alert/Explainability pipeline degraded: %s", e)

    breakdown = [
        SignalBreakdown(
            signal_name=s.signal_name,
            weight=s.weight,
            raw_value=s.raw_value,
            normalized_score=s.normalized_score,
            explanation=s.explanation,
        )
        for s in risk_score_obj.signals
    ]

    return TransactionPredictResponse(
        fraud_probability=fraud_prob,
        risk_score=score,
        is_fraud_suspected=is_fraud_suspected,
        risk_level=risk_level,
        breakdown=breakdown,
        alert_details=alert_details,
    )
