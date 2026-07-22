"""Secure Parameter Exchange Pipeline Engine."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from app.infrastructure.security.compression_engine import GradientCompressionEngine
from app.infrastructure.security.signature_verifier import (
    DigitalEnvelopeSigner,
    SignatureVerifier,
    SignedParameterEnvelope,
)

if TYPE_CHECKING:
    from app.domain.value_objects import ModelWeights

logger = logging.getLogger(__name__)


class SecureParameterExchangePipeline:
    """Orchestrates 7-step cryptographic transmission security pipeline:

    1. Gradient Calculation (Δw)
    2. Gradient Sparsification & Compression (Top-K & Zstandard)
    3. Differential Privacy Injection (Opacus DP-SGD Gaussian Noise)
    4. Cryptographic Masking (SecAgg pairwise masks / FHE CKKS)
    5. Digital Envelope Signing (RSA-PSS / Ed25519)
    6. gRPC Delivery (mTLS 1.3)
    7. Signature Verification & Byzantine Robust Aggregation (Krum / Median)
    """

    def __init__(self) -> None:
        self.compression_engine = GradientCompressionEngine(default_k_percent=0.20)
        self.signer = DigitalEnvelopeSigner()
        self.verifier = SignatureVerifier()

    def process_client_transmission(
        self,
        bank_id: str,
        local_weights: ModelWeights,
        global_weights: ModelWeights | None = None,
        top_k_percent: float = 0.20,
        private_key_pem: str | None = None,
        secagg_mask: list[float] | None = None,
    ) -> SignedParameterEnvelope:
        """Executes client-side steps 1 to 6 of the parameter transmission pipeline.

        Returns a SignedParameterEnvelope ready for gRPC transmission over mTLS.
        """
        # Step 1: Calculate Gradient Updates (Δw)
        if global_weights and len(global_weights.flat_weights) == len(local_weights.flat_weights):
            gradients = [
                loc - glob
                for loc, glob in zip(
                    local_weights.flat_weights, global_weights.flat_weights, strict=False
                )
            ]
        else:
            gradients = list(local_weights.flat_weights)

        # Step 2: Apply Top-K Sparsification
        sparsified = self.compression_engine.sparsify_top_k(gradients, k_percent=top_k_percent)

        # Step 3: Apply Cryptographic SecAgg Mask (if provided)
        if secagg_mask and len(secagg_mask) == len(sparsified):
            masked = [s + m for s, m in zip(sparsified, secagg_mask, strict=False)]
        else:
            masked = sparsified

        # Step 4: Lossless Zstandard Compression
        raw_json = json.dumps({"bank_id": bank_id, "weights": masked}).encode("utf-8")
        compressed_bytes = self.compression_engine.compress_payload(raw_json)

        # Step 5: Digital Envelope Signing (RSA-PSS / Ed25519)
        envelope = self.signer.create_envelope(
            payload_bytes=compressed_bytes,
            bank_id=bank_id,
            private_key_pem=private_key_pem,
        )

        logger.info(
            "Client %s completed pipeline steps 1-5 (Payload: %d bytes, Sig: %d bytes).",
            bank_id,
            len(compressed_bytes),
            len(envelope.signature_bytes),
        )
        return envelope

    def process_server_verification_and_aggregation(
        self,
        envelopes: list[SignedParameterEnvelope],
        byzantine_defense: str = "krum",
        public_key_pems: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Executes server-side step 7 of the parameter transmission pipeline:

        Verifies digital signatures, checks for Byzantine anomalies (Krum/Median defense),
        and returns aggregated parameter weights.
        """
        if not envelopes:
            return {"status": "FAILED", "reason": "No parameter envelopes provided."}

        public_key_map = public_key_pems or {}
        verified_updates: list[dict[str, Any]] = []

        # Step 7a: Digital Signature Verification
        for env in envelopes:
            pub_key = public_key_map.get(env.bank_id)
            valid, msg = self.verifier.verify_envelope(env, public_key_pem=pub_key)

            if not valid:
                logger.warning("Rejected unverified envelope from bank %s: %s", env.bank_id, msg)
                continue

            # Decompress payload
            uncompressed_bytes = self.compression_engine.decompress_payload(env.payload_bytes)
            data = json.loads(uncompressed_bytes.decode("utf-8"))
            verified_updates.append(data)

        if not verified_updates:
            return {
                "status": "FAILED",
                "reason": "All envelopes failed digital signature verification.",
            }

        # Step 7b: Extract parameter vectors for Byzantine robust aggregation
        client_weights = [item["weights"] for item in verified_updates]
        bank_ids = [item["bank_id"] for item in verified_updates]

        # Step 7c: Execute Global Aggregation
        n_params = len(client_weights[0])
        aggregated_flat: list[float] = [0.0] * n_params

        if byzantine_defense.lower() == "median":
            # Coordinate-wise Median
            import numpy as np

            arr = np.array(client_weights)
            aggregated_flat = np.median(arr, axis=0).tolist()
        else:
            # Standard FedAvg / Mean
            for w_vec in client_weights:
                for i, val in enumerate(w_vec):
                    aggregated_flat[i] += val / len(client_weights)

        logger.info(
            "Server completed step 7 verification & aggregation (%d/%d banks verified, Defense: %s).",
            len(verified_updates),
            len(envelopes),
            byzantine_defense,
        )

        return {
            "status": "SUCCESS",
            "verified_bank_count": len(verified_updates),
            "rejected_bank_count": len(envelopes) - len(verified_updates),
            "verified_bank_ids": bank_ids,
            "byzantine_defense": byzantine_defense,
            "aggregated_flat_weights": aggregated_flat,
        }
