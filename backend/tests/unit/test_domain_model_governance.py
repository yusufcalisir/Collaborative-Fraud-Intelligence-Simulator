"""Unit tests for Model Governance, Dual Sign-off Gating, Shadowing, and Automatic Rollbacks."""

from __future__ import annotations

from app.domain.model_governance import (
    AutomaticRollbackTrigger,
    CryptographicAuditLineage,
    DualSignoffGate,
    SemanticVersion,
    ShadowDeploymentEngine,
)


def test_semantic_version_parsing_and_bumping() -> None:
    """Verifies SemanticVersion parsing, comparison, formatting, and tag bumping."""
    v1 = SemanticVersion.parse("v1.2.3")
    assert v1.major == 1
    assert v1.minor == 2
    assert v1.patch == 3
    assert v1.to_tag() == "v1.2.3"

    v2 = v1.bump_patch()
    assert v2.to_tag() == "v1.2.4"

    v3 = v1.bump_minor()
    assert v3.to_tag() == "v1.3.0"

    v4 = v1.bump_major()
    assert v4.to_tag() == "v2.0.0"

    assert v1 < v4
    assert v4 > v2


def test_dual_signoff_gate_enforcement() -> None:
    """Verifies DualSignoffGate requires both ML Engineer and Compliance Officer sign-offs."""
    gate = DualSignoffGate()

    # 1. No sign-offs provided
    can_prom1, msg1 = gate.can_promote([])
    assert can_prom1 is False
    assert "No sign-offs provided" in msg1

    # 2. Only ML Engineer signoff provided
    ml_sign = [{"role": "ml_engineer", "user": "eng_lead", "signature": "sig_ml_123"}]
    can_prom2, msg2 = gate.can_promote(ml_sign)
    assert can_prom2 is False
    assert "compliance_officer" in msg2

    # 3. Dual signoff provided (ML Engineer + Compliance Officer)
    dual_signs = [
        {"role": "ml_engineer", "user": "eng_lead", "signature": "sig_ml_123"},
        {"role": "compliance_officer", "user": "officer_alice", "signature": "sig_comp_456"},
    ]
    can_prom3, msg3 = gate.can_promote(dual_signs)
    assert can_prom3 is True
    assert "Dual Signoff Gate Passed" in msg3


def test_shadow_deployment_engine_routing() -> None:
    """Verifies ShadowDeploymentEngine 10% shadow traffic routing and evaluation."""
    engine = ShadowDeploymentEngine(shadow_ratio=0.10)

    # Test deterministic hash routing
    routed_count = sum(1 for i in range(1000) if engine.should_route_to_shadow(f"req_{i}"))
    # Expect approximately 100 out of 1000 requests (allowing 70-130 range)
    assert 70 <= routed_count <= 130

    # Test shadow performance evaluation
    eval_res = engine.evaluate_shadow_performance(champion_auc=0.75, shadow_auc=0.82)
    assert eval_res["is_superior"] is True
    assert eval_res["recommendation"] == "PROMOTE_SHADOW_TO_CHAMPION"


def test_automatic_rollback_trigger() -> None:
    """Verifies AutomaticRollbackTrigger triggers on ROC-AUC < 0.65 or p99 latency > 200ms."""
    trigger = AutomaticRollbackTrigger(min_auc_roc=0.65, max_p99_latency_ms=200.0)

    # 1. Nominal telemetry passes
    roll1, msg1 = trigger.should_rollback(live_auc_roc=0.85, p99_latency_ms=120.0)
    assert roll1 is False

    # 2. Low ROC-AUC (< 0.65) triggers rollback
    roll2, msg2 = trigger.should_rollback(live_auc_roc=0.61, p99_latency_ms=120.0)
    assert roll2 is True
    assert "fell below minimum safety threshold" in msg2

    # 3. High p99 latency (> 200ms) triggers rollback
    roll3, msg3 = trigger.should_rollback(live_auc_roc=0.85, p99_latency_ms=245.0)
    assert roll3 is True
    assert "exceeded maximum threshold" in msg3


def test_cryptographic_audit_lineage_manifest() -> None:
    """Verifies CryptographicAuditLineage manifest structure and serialization."""
    lineage = CryptographicAuditLineage(
        model_version="v2.1.0",
        git_commit_hash="commit_hash_789",
        dataset_hash="dataset_sha256_456",
        dp_epsilon=0.5,
        dp_delta=1e-5,
        sign_offs=[{"role": "ml_engineer", "user": "user1"}],
    )

    manifest = lineage.to_dict()
    assert manifest["model_version"] == "v2.1.0"
    assert manifest["git_commit_hash"] == "commit_hash_789"
    assert manifest["dp_privacy_budget"]["epsilon"] == 0.5
    assert len(manifest["sign_offs"]) == 1
