import logging
import time
from typing import Any
import numpy as np

from app.domain.value_objects import ModelWeights

logger = logging.getLogger(__name__)


class FHEKeyRing:
    """Contains public, secret, and evaluation keys for simulated FHE."""

    def __init__(self, key_id: str, poly_degree: int = 4096) -> None:
        self.key_id = key_id
        self.poly_degree = poly_degree
        self.public_key = f"fhe_pub_key_{key_id[:8]}"
        self.secret_key = f"fhe_sec_key_{key_id[:8]}"
        self.eval_key = f"fhe_eval_key_{key_id[:8]}"


class EncryptedWeights:
    """Represents encrypted model parameters using simulated FHE."""

    def __init__(self, ciphertexts: list[float], key_id: str, noise_bound: float) -> None:
        self.ciphertexts = ciphertexts
        self.key_id = key_id
        self.noise_bound = noise_bound


class FHEDriver:
    """Simulates Fully Homomorphic Encryption (FHE) for secure weights aggregation.

    This driver simulates homomorphic evaluation overhead (e.g., CKKS scheme),
    allowing calculation of client averages over encrypted states.
    """

    @staticmethod
    def generate_keys(simulation_id: str) -> FHEKeyRing:
        """Generate simulated public/private/evaluation key ring."""
        start_time = time.perf_counter()
        # Simulate poly degree generation overhead (e.g., 200ms)
        time.sleep(0.15)
        key_ring = FHEKeyRing(simulation_id)
        duration = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Generated FHE Keyring for %s (Poly Degree: %d) in %.2fms",
            simulation_id,
            key_ring.poly_degree,
            duration,
        )
        return key_ring

    @staticmethod
    def encrypt_weights(
        weights: ModelWeights, key_ring: FHEKeyRing, rng: np.random.Generator | None = None
    ) -> EncryptedWeights:
        """Encrypt float weights into ciphertexts with simulated cryptographic noise."""
        if rng is None:
            rng = np.random.default_rng()

        start_time = time.perf_counter()

        # Simulate CKKS encryption noise (modulus Q / error e)
        # e ~ N(0, 1e-9)
        error_scale = 1e-9
        flat_arr = np.array(weights.flat_weights)
        noise = rng.normal(0, error_scale, len(flat_arr))
        ciphertexts = (flat_arr + noise).tolist()

        # Simulate FHE encryption latency (e.g., 0.1ms per 100 parameters)
        param_count = len(flat_arr)
        sleep_time = min(0.3, param_count * 0.0001)
        time.sleep(sleep_time)

        duration = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Encrypted %d parameters using FHE key %s in %.2fms",
            param_count,
            key_ring.public_key,
            duration,
        )

        return EncryptedWeights(
            ciphertexts=ciphertexts,
            key_id=key_ring.key_id,
            noise_bound=error_scale,
        )

    @staticmethod
    def homomorphic_average(
        encrypted_updates: list[EncryptedWeights],
        client_samples: list[int] | None = None,
    ) -> EncryptedWeights:
        """Perform homomorphic weighted averaging directly over ciphertexts."""
        start_time = time.perf_counter()

        n_clients = len(encrypted_updates)
        n_params = len(encrypted_updates[0].ciphertexts)
        key_id = encrypted_updates[0].key_id

        # Homomorphic addition is a linear operation:
        # Sum_i (c_i * w_i)
        if client_samples is None:
            weights = [1.0 / n_clients] * n_clients
        else:
            total_samples = sum(client_samples)
            if total_samples > 0:
                weights = [s / total_samples for s in client_samples]
            else:
                weights = [1.0 / n_clients] * n_clients

        accumulated = np.zeros(n_params)
        for i, enc in enumerate(encrypted_updates):
            if enc.key_id != key_id:
                raise ValueError("Mismatched FHE keys during homomorphic aggregation.")
            accumulated += np.array(enc.ciphertexts) * weights[i]

        # Simulate homomorphic multiplication/addition overhead (1.5ms per 100 params)
        sleep_time = min(0.4, n_params * 0.00015 * n_clients)
        time.sleep(sleep_time)

        duration = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Completed homomorphic average over %d ciphertexts (params: %d) in %.2fms",
            n_clients,
            n_params,
            duration,
        )

        # Noise grows during homomorphic additions
        final_noise = float(np.sqrt(sum(w**2 for w in weights)) * encrypted_updates[0].noise_bound)

        return EncryptedWeights(
            ciphertexts=accumulated.tolist(),
            key_id=key_id,
            noise_bound=final_noise,
        )

    @staticmethod
    def decrypt_weights(
        encrypted_weights: EncryptedWeights,
        key_ring: FHEKeyRing,
        layer_shapes: list[tuple[int, ...]],
    ) -> ModelWeights:
        """Decrypt ciphertext back to plaintext float ModelWeights."""
        if encrypted_weights.key_id != key_ring.key_id:
            raise ValueError("Invalid secret key for decryption.")

        start_time = time.perf_counter()

        # Decryption removes the mask layer (simulated)
        flat_weights = encrypted_weights.ciphertexts

        # Simulate FHE decryption latency
        param_count = len(flat_weights)
        sleep_time = min(0.2, param_count * 0.00008)
        time.sleep(sleep_time)

        duration = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Decrypted %d parameters using FHE key %s in %.2fms",
            param_count,
            key_ring.secret_key,
            duration,
        )

        return ModelWeights(
            layer_shapes=layer_shapes,
            flat_weights=flat_weights,
        )
