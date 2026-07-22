"""Unit tests for Secure Parameter Exchange Pipeline Engine, Compression, and Signature Verifier."""

from __future__ import annotations

from app.domain.value_objects import ModelWeights
from app.infrastructure.security.compression_engine import GradientCompressionEngine
from app.infrastructure.security.secure_parameter_pipeline import SecureParameterExchangePipeline
from app.infrastructure.security.signature_verifier import (
    DigitalEnvelopeSigner,
    SignatureVerifier,
    SignedParameterEnvelope,
)


def test_gradient_compression_engine_sparsification_and_compression() -> None:
    """Verifies Top-K gradient sparsification and lossless compression / decompression."""
    engine = GradientCompressionEngine(default_k_percent=0.20)

    raw_weights = [0.1, 5.0, 0.02, -8.5, 0.001, 12.0, 0.05, -0.01, 0.03, 15.0]
    sparsified = engine.sparsify_top_k(raw_weights, k_percent=0.20)

    # 20% of 10 items = top 2 items (15.0 and 12.0)
    assert sum(1 for w in sparsified if w != 0.0) == 2
    assert 15.0 in sparsified
    assert 12.0 in sparsified

    # Lossless compression roundtrip
    data_bytes = b"Hello, Federated Learning Transmission Payload 2026!"
    compressed = engine.compress_payload(data_bytes)
    assert len(compressed) > 0

    decompressed = engine.decompress_payload(compressed)
    assert decompressed == data_bytes


def test_digital_envelope_signing_and_verification() -> None:
    """Verifies DigitalEnvelopeSigner signing, SignatureVerifier validation, and tampered payload rejection."""
    signer = DigitalEnvelopeSigner(signing_secret="secret_key_2026")
    verifier = SignatureVerifier(signing_secret="secret_key_2026")

    payload = b"encrypted_model_update_payload_bytes_12345"
    bank_id = "bank_alpha"

    envelope = signer.create_envelope(payload_bytes=payload, bank_id=bank_id)
    assert isinstance(envelope, SignedParameterEnvelope)

    # Signature verification passes for valid payload
    valid, msg = verifier.verify_envelope(envelope)
    assert valid is True
    assert "verified" in msg

    # Signature verification fails for tampered payload
    tampered_envelope = SignedParameterEnvelope(
        bank_id=bank_id,
        payload_bytes=b"tampered_payload_bytes",
        signature_bytes=envelope.signature_bytes,
    )
    invalid, err_msg = verifier.verify_envelope(tampered_envelope)
    assert invalid is False
    assert "Signature Mismatch" in err_msg


def test_secure_parameter_exchange_pipeline_end_to_end() -> None:
    """Verifies end-to-end 7-step transmission security pipeline."""
    pipeline = SecureParameterExchangePipeline()

    weights_a = ModelWeights(layer_shapes=[(5,)], flat_weights=[1.0, 2.0, 3.0, 4.0, 5.0])
    weights_b = ModelWeights(layer_shapes=[(5,)], flat_weights=[1.2, 1.8, 3.1, 3.9, 5.2])

    # Step 1-5: Client transmission creation
    env_a = pipeline.process_client_transmission(
        bank_id="bank_a", local_weights=weights_a, top_k_percent=1.0
    )
    env_b = pipeline.process_client_transmission(
        bank_id="bank_b", local_weights=weights_b, top_k_percent=1.0
    )

    assert env_a.bank_id == "bank_a"
    assert env_b.bank_id == "bank_b"

    # Step 7: Server verification and Byzantine robust aggregation
    agg_result = pipeline.process_server_verification_and_aggregation(
        envelopes=[env_a, env_b], byzantine_defense="median"
    )

    assert agg_result["status"] == "SUCCESS"
    assert agg_result["verified_bank_count"] == 2
    assert "aggregated_flat_weights" in agg_result
    assert len(agg_result["aggregated_flat_weights"]) == 5
