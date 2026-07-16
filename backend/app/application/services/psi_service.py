"""Diffie-Hellman Private Set Intersection (DH-PSI) Service.

Simulates a zero-knowledge cross-institution client matching protocol.
"""

from __future__ import annotations

import logging
import secrets
import time
from typing import TYPE_CHECKING, Any

from app.application.services.entity_resolution import EntityResolutionService

if TYPE_CHECKING:
    from app.domain.enums import EntityType

logger = logging.getLogger(__name__)

# Standard 512-bit modular exponentiation prime
PSI_PRIME = 0xDEB00B9C694F4BE84A28B101E6A0F1D8B9646D0BF1A0F53FBAFF74205A405D021C7B38A8DE5F482F6B8470E04E5FCEF5BA88CEB8E5E7A0D0BF7BCAAA83DE4F2D
PRIME_BIT_LENGTH = 512


class PSIService:
    """Orchestrates DH-PSI simulation between two banks."""

    def __init__(self, entity_service: EntityResolutionService | None = None) -> None:
        self.entity_service = entity_service or EntityResolutionService()

    def run_psi(
        self,
        bank_a_id: str,
        bank_b_id: str,
        entity_type: EntityType | None = None,
        enable_tee: bool = False,
    ) -> dict[str, Any]:
        """Execute simulated DH-PSI between Bank A and Bank B, with optional TEE enclave simulation.

        Args:
            bank_a_id: ID of the first bank.
            bank_b_id: ID of the second bank.
            entity_type: Optional filter on entity types (CUSTOMER, DEVICE, etc.).
            enable_tee: If True, executes the matching inside a simulated Secure Hardware Enclave.

        Returns:
            Dict containing matched entities list and protocol stats.
        """
        start_time = time.perf_counter()

        # 1. Retrieve all entities for each bank from storage
        all_entities = self.entity_service.get_entities(entity_type=entity_type, limit=1000)
        entities_a = [e for e in all_entities if e.bank_id == bank_a_id]
        entities_b = [e for e in all_entities if e.bank_id == bank_b_id]

        if not entities_a or not entities_b:
            # Return empty structure
            elapsed = (time.perf_counter() - start_time) * 1000.0
            return {
                "matches": [],
                "stats": {
                    "computation_time_ms": round(elapsed, 2),
                    "data_exchanged_bytes": 0,
                    "num_entities_a": len(entities_a),
                    "num_entities_b": len(entities_b),
                    "prime_bit_length": PRIME_BIT_LENGTH,
                    "enclave_execution": enable_tee,
                },
            }

        if enable_tee:
            # Simulated Secure Hardware Enclave (SGX/SEV) matching:
            # Bypasses modular exponentiation overhead through hardware acceleration,
            # performing secure entity resolution inside TEE memory boundaries.
            common_hashes = set(e.privacy_id for e in entities_a) & set(
                e.privacy_id for e in entities_b
            )
            entities_a_by_hash = {e.privacy_id: e for e in entities_a}
            entities_b_by_hash = {e.privacy_id: e for e in entities_b}
            matches = []
            for h in common_hashes:
                ent_a = entities_a_by_hash[h]
                ent_b = entities_b_by_hash[h]
                matches.append(
                    {
                        "privacy_hash": ent_a.privacy_id,
                        "entity_type": ent_a.entity_type.value,
                        "display_label_a": ent_a.display_label,
                        "display_label_b": ent_b.display_label,
                        "risk_level_a": ent_a.risk_level.value,
                        "risk_level_b": ent_b.risk_level.value,
                    }
                )

            # Attestation measurements
            mrenclave = "0x8fae3f19114d7a8e84a28b101e6a0f1d8b9646d0bf1a0f53fbaff74205a405d0"
            mrsigner = "0xc4b220e897bd21ab163a3d5e2e8df81f7290c0ef49748bdf5f2a1b24d7bc902c"

            # Less data exchanged because only initial hashes are shared over TEE rather than double encryptions
            data_exchanged = (len(entities_a) + len(entities_b)) * (PRIME_BIT_LENGTH // 8)

            end_time = time.perf_counter()
            elapsed_ms = ((end_time - start_time) * 1000.0) / 15.0  # simulated 15x hardware speedup

            stats = {
                "computation_time_ms": round(elapsed_ms, 2),
                "data_exchanged_bytes": data_exchanged,
                "num_entities_a": len(entities_a),
                "num_entities_b": len(entities_b),
                "enclave_execution": True,
                "mrenclave": mrenclave,
                "mrsigner": mrsigner,
                "attestation_verified": True,
            }
        else:
            # 2. Generate private key scalars (simulated DH keys)
            key_a = secrets.randbelow(PSI_PRIME - 2) + 2
            key_b = secrets.randbelow(PSI_PRIME - 2) + 2

            # 3. Pass 1: Local Encryption
            # Convert hex privacy_id to int, then raise to modular power
            encrypted_a = []
            for e in entities_a:
                val_int = int(e.privacy_id, 16)
                enc_val = pow(val_int, key_a, PSI_PRIME)
                encrypted_a.append((e, enc_val))

            encrypted_b = []
            for e in entities_b:
                val_int = int(e.privacy_id, 16)
                enc_val = pow(val_int, key_b, PSI_PRIME)
                encrypted_b.append((e, enc_val))

            # 4. Pass 2: Cross Encryption (simulate exchange and re-encryption)
            double_encrypted_a = {}
            for entity_a, enc_val in encrypted_a:
                double_enc = pow(enc_val, key_b, PSI_PRIME)
                double_encrypted_a[double_enc] = entity_a

            double_encrypted_b = {}
            for entity_b, enc_val in encrypted_b:
                double_enc = pow(enc_val, key_a, PSI_PRIME)
                double_encrypted_b[double_enc] = entity_b

            # 5. Intersect double-encrypted values
            common_keys = set(double_encrypted_a.keys()) & set(double_encrypted_b.keys())
            matches = []
            for k in common_keys:
                ent_a = double_encrypted_a[k]
                ent_b = double_encrypted_b[k]
                matches.append(
                    {
                        "privacy_hash": ent_a.privacy_id,
                        "entity_type": ent_a.entity_type.value,
                        "display_label_a": ent_a.display_label,
                        "display_label_b": ent_b.display_label,
                        "risk_level_a": ent_a.risk_level.value,
                        "risk_level_b": ent_b.risk_level.value,
                    }
                )

            element_bytes = PRIME_BIT_LENGTH // 8
            data_exchanged = 2 * (len(entities_a) + len(entities_b)) * element_bytes

            end_time = time.perf_counter()
            elapsed_ms = (end_time - start_time) * 1000.0

            stats = {
                "computation_time_ms": round(elapsed_ms, 2),
                "data_exchanged_bytes": data_exchanged,
                "num_entities_a": len(entities_a),
                "num_entities_b": len(entities_b),
                "prime_bit_length": PRIME_BIT_LENGTH,
                "enclave_execution": False,
            }

        logger.info(
            "DH-PSI protocol executed between %s and %s (TEE: %s). Found %d matches in %.2fms. Data exchanged: %d bytes.",
            bank_a_id,
            bank_b_id,
            enable_tee,
            len(matches),
            elapsed_ms,
            data_exchanged,
        )

        return {
            "matches": matches,
            "stats": stats,
        }
