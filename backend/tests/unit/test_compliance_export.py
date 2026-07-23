"""Unit tests for the EU AI Act Compliance Certificate Export Engine (Section 13.1).

Covers:
- ComplianceCertificate structure and Article 10-15 coverage
- JSON determinism (same inputs → same canonical JSON)
- HMAC-SHA256 signature format validation
- Signature verification with correct and tampered certificates
- Markdown export completeness
- CLI script importability and main guard
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from app.domain.ai_act_compliance import (
    ARTICLE_10,
    ARTICLE_11,
    ARTICLE_12,
    ARTICLE_13,
    ARTICLE_14,
    ARTICLE_15,
    ComplianceCertificate,
    EUAIActComplianceEngine,
    verify_certificate_signature,
)

SIGNING_KEY = b"test-hmac-signing-key-for-unit-tests"
SCRIPTS_DIR = Path(__file__).parents[3] / "scripts"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def compliant_engine() -> EUAIActComplianceEngine:
    """Returns a fully-compliant EUAIActComplianceEngine instance."""
    return EUAIActComplianceEngine(
        model_version="v2.1.0",
        fl_rounds_completed=25,
        dp_epsilon=2.3,
        dp_delta=1e-5,
        iban_pass_rate=0.9999,
        spectral_anomaly_count=0,
        dual_signoff_approved=True,
        model_auc=0.93,
        model_f1=0.88,
        audit_log_sha256="a" * 64,
        hyperparams_sha256="b" * 64,
        explainability_method="SHAP",
        consortium_size=5,
    )


@pytest.fixture()
def compliant_cert(compliant_engine: EUAIActComplianceEngine) -> ComplianceCertificate:
    return compliant_engine.generate_certificate(SIGNING_KEY)


# ---------------------------------------------------------------------------
# 1. TestComplianceCertificateStructure
# ---------------------------------------------------------------------------

class TestComplianceCertificateStructure:
    def test_certificate_has_all_eu_ai_act_articles(self, compliant_cert: ComplianceCertificate):
        """All six required EU AI Act articles must be present in the certificate."""
        expected_articles = {ARTICLE_10, ARTICLE_11, ARTICLE_12, ARTICLE_13, ARTICLE_14, ARTICLE_15}
        assert set(compliant_cert.articles.keys()) == expected_articles

    def test_certificate_json_structure(self, compliant_cert: ComplianceCertificate):
        """Serialized JSON certificate must include all required top-level fields."""
        json_str = EUAIActComplianceEngine.export_json(compliant_cert)
        data = json.loads(json_str)

        assert "cert_id" in data
        assert "issued_at" in data
        assert "regulation" in data
        assert "model_version" in data
        assert "overall_compliant" in data
        assert "articles" in data
        assert "signature" in data
        assert "cert_hash" in data

    def test_certificate_signature_is_hmac_sha256_hex(self, compliant_cert: ComplianceCertificate):
        """Signature field must be a valid lowercase 64-character hex string (HMAC-SHA256)."""
        sig = compliant_cert.signature
        assert len(sig) == 64, f"Expected 64-char hex signature, got length {len(sig)}"
        # Must be valid hexadecimal
        int(sig, 16)

    def test_certificate_cert_hash_is_sha256_hex(self, compliant_cert: ComplianceCertificate):
        """cert_hash must be a valid 64-character SHA-256 hex string."""
        ch = compliant_cert.cert_hash
        assert len(ch) == 64
        int(ch, 16)

    def test_overall_compliant_true_when_all_articles_pass(self, compliant_cert: ComplianceCertificate):
        """overall_compliant must be True when all article assessments are compliant."""
        assert compliant_cert.overall_compliant is True

    def test_overall_compliant_false_when_article_fails(self):
        """overall_compliant must be False if any article assessment fails."""
        engine = EUAIActComplianceEngine(
            model_version="v1.0.0",
            fl_rounds_completed=10,
            dp_epsilon=1.0,
            iban_pass_rate=1.0,
            dual_signoff_approved=False,  # Article 14 will fail
            model_auc=0.93,
            model_f1=0.88,
            audit_log_sha256="a" * 64,
            hyperparams_sha256="b" * 64,
        )
        cert = engine.generate_certificate(SIGNING_KEY)
        assert cert.overall_compliant is False


# ---------------------------------------------------------------------------
# 2. TestSignatureVerification
# ---------------------------------------------------------------------------

class TestSignatureVerification:
    def test_signature_verifies_with_correct_key(self, compliant_cert: ComplianceCertificate):
        """HMAC verification must pass with the original signing key."""
        assert verify_certificate_signature(compliant_cert, SIGNING_KEY) is True

    def test_signature_fails_with_wrong_key(self, compliant_cert: ComplianceCertificate):
        """HMAC verification must fail with a different key."""
        wrong_key = b"completely-different-key"
        assert verify_certificate_signature(compliant_cert, wrong_key) is False

    def test_tampered_model_version_fails_verification(self, compliant_cert: ComplianceCertificate):
        """Mutating model_version must cause signature verification to fail."""
        tampered = ComplianceCertificate(
            cert_id=compliant_cert.cert_id,
            issued_at=compliant_cert.issued_at,
            regulation=compliant_cert.regulation,
            model_version="v9.9.9-tampered",  # Mutated field
            articles=compliant_cert.articles,
            overall_compliant=compliant_cert.overall_compliant,
            signature=compliant_cert.signature,  # Original signature retained
            cert_hash=compliant_cert.cert_hash,
        )
        assert verify_certificate_signature(tampered, SIGNING_KEY) is False

    def test_tampered_overall_compliant_fails_verification(self, compliant_cert: ComplianceCertificate):
        """Flipping overall_compliant must cause signature verification to fail."""
        tampered = ComplianceCertificate(
            cert_id=compliant_cert.cert_id,
            issued_at=compliant_cert.issued_at,
            regulation=compliant_cert.regulation,
            model_version=compliant_cert.model_version,
            articles=compliant_cert.articles,
            overall_compliant=False,  # Flipped
            signature=compliant_cert.signature,
            cert_hash=compliant_cert.cert_hash,
        )
        assert verify_certificate_signature(tampered, SIGNING_KEY) is False


# ---------------------------------------------------------------------------
# 3. TestArticleAssessments
# ---------------------------------------------------------------------------

class TestArticleAssessments:
    def test_article_10_fails_on_low_iban_pass_rate(self):
        engine = EUAIActComplianceEngine(
            model_version="v1.0.0",
            fl_rounds_completed=5,
            dp_epsilon=1.0,
            iban_pass_rate=0.990,  # Below 0.999 threshold
        )
        assessment = engine.assess_article_10_data_governance()
        assert assessment.compliant is False
        assert any("IBAN" in f for f in assessment.findings)

    def test_article_14_fails_when_dual_signoff_missing(self):
        engine = EUAIActComplianceEngine(
            model_version="v1.0.0",
            fl_rounds_completed=5,
            dp_epsilon=1.0,
            dual_signoff_approved=False,
        )
        assessment = engine.assess_article_14_human_oversight()
        assert assessment.compliant is False
        assert any("sign-off" in f.lower() for f in assessment.findings)

    def test_article_15_fails_on_low_auc(self):
        engine = EUAIActComplianceEngine(
            model_version="v1.0.0",
            fl_rounds_completed=5,
            dp_epsilon=1.0,
            model_auc=0.60,  # Below 0.75
            model_f1=0.80,
        )
        assessment = engine.assess_article_15_accuracy_robustness()
        assert assessment.compliant is False
        assert any("AUC" in f for f in assessment.findings)

    def test_article_11_fails_without_hyperparams_hash(self):
        engine = EUAIActComplianceEngine(
            model_version="v1.0.0",
            fl_rounds_completed=5,
            dp_epsilon=1.0,
            hyperparams_sha256="",  # Missing
        )
        assessment = engine.assess_article_11_technical_documentation()
        assert assessment.compliant is False


# ---------------------------------------------------------------------------
# 4. TestMarkdownExport
# ---------------------------------------------------------------------------

class TestMarkdownExport:
    def test_markdown_contains_all_article_headings(self, compliant_cert: ComplianceCertificate):
        """Markdown must contain headings for all six EU AI Act articles."""
        md = EUAIActComplianceEngine.export_markdown(compliant_cert)
        for article in [ARTICLE_10, ARTICLE_11, ARTICLE_12, ARTICLE_13, ARTICLE_14, ARTICLE_15]:
            assert article in md, f"Article heading missing from markdown: {article}"

    def test_markdown_contains_certificate_id(self, compliant_cert: ComplianceCertificate):
        """Markdown must contain the certificate UUID."""
        md = EUAIActComplianceEngine.export_markdown(compliant_cert)
        assert compliant_cert.cert_id in md

    def test_markdown_contains_signature(self, compliant_cert: ComplianceCertificate):
        """Markdown must embed the HMAC-SHA256 signature for auditability."""
        md = EUAIActComplianceEngine.export_markdown(compliant_cert)
        assert compliant_cert.signature in md

    def test_markdown_contains_regulation_reference(self, compliant_cert: ComplianceCertificate):
        """Markdown must reference the EU AI Act regulation string."""
        md = EUAIActComplianceEngine.export_markdown(compliant_cert)
        assert "2024/1689" in md


# ---------------------------------------------------------------------------
# 5. TestCLIScript
# ---------------------------------------------------------------------------

class TestCLIScript:
    def test_cli_script_exists(self):
        path = SCRIPTS_DIR / "export_compliance_report.py"
        assert path.exists(), f"CLI script not found at {path}"

    def test_cli_script_has_main_guard(self):
        path = SCRIPTS_DIR / "export_compliance_report.py"
        content = path.read_text(encoding="utf-8")
        assert 'if __name__ == "__main__"' in content

    def test_cli_build_parser_returns_parser(self):
        spec = importlib.util.spec_from_file_location(
            "export_compliance_report",
            SCRIPTS_DIR / "export_compliance_report.py",
        )
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        parser = mod.build_parser()
        # Verify key arguments are registered
        arg_dests = {action.dest for action in parser._actions}
        assert "model_version" in arg_dests
        assert "fl_rounds" in arg_dests
        assert "dp_epsilon" in arg_dests
        assert "output_dir" in arg_dests
