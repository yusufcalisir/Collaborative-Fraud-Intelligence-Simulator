"""Gradient Sparsification & Lossless Compression Engine."""

from __future__ import annotations

import logging
import zlib
from typing import Any

logger = logging.getLogger(__name__)


class GradientCompressionEngine:
    """Provides Top-K gradient sparsification and lossless Zstandard/zlib payload compression.

    Reduces network transmission bandwidth for federated parameter updates.
    """

    def __init__(self, default_k_percent: float = 0.20) -> None:
        self.default_k_percent = default_k_percent

    def sparsify_top_k(
        self, weights_flat: list[float], k_percent: float | None = None
    ) -> list[float]:
        """Applies Top-K gradient sparsification.

        Retains the top K% highest absolute magnitude elements in the gradient vector,
        zeroing out non-essential parameters.
        """
        if not weights_flat:
            return []

        k_pct = k_percent if k_percent is not None else self.default_k_percent
        k_pct = max(0.01, min(1.0, k_pct))  # Clamp between 1% and 100%

        n = len(weights_flat)
        k_count = max(1, int(n * k_pct))

        # Find threshold value corresponding to k_count highest absolute values
        abs_vals = [abs(w) for w in weights_flat]
        abs_vals_sorted = sorted(abs_vals, reverse=True)
        threshold = abs_vals_sorted[k_count - 1] if k_count <= len(abs_vals_sorted) else 0.0

        # Zero out elements below threshold
        sparsified = [w if abs(w) >= threshold else 0.0 for w in weights_flat]

        non_zero_count = sum(1 for w in sparsified if w != 0.0)
        logger.debug(
            "Top-K sparsification (K=%.1f%%): %d non-zero elements retained out of %d total parameters.",
            k_pct * 100.0,
            non_zero_count,
            n,
        )
        return sparsified

    def compress_payload(self, data_bytes: bytes, level: int = 6) -> bytes:
        """Compresses byte payload using zlib/zstd lossless compression."""
        if not data_bytes:
            return b""

        compressed = zlib.compress(data_bytes, level=level)
        ratio = (1.0 - (len(compressed) / float(len(data_bytes)))) * 100.0
        logger.debug(
            "Payload compressed: %d bytes -> %d bytes (Compression ratio: %.1f%%).",
            len(data_bytes),
            len(compressed),
            ratio,
        )
        return compressed

    def decompress_payload(self, compressed_bytes: bytes) -> bytes:
        """Decompresses lossless compressed payload back into raw bytes."""
        if not compressed_bytes:
            return b""

        return zlib.decompress(compressed_bytes)

    def compress_gradient_vector(
        self, weights_flat: list[float], k_percent: float | None = None
    ) -> dict[str, Any]:
        """Sparsifies and compresses a flat gradient vector, returning payload metadata."""
        import json

        sparsified = self.sparsify_top_k(weights_flat, k_percent=k_percent)
        raw_json = json.dumps(sparsified).encode("utf-8")
        compressed_bytes = self.compress_payload(raw_json)

        return {
            "original_length": len(weights_flat),
            "sparsified_length": len(sparsified),
            "compressed_bytes": compressed_bytes,
            "compressed_size": len(compressed_bytes),
            "raw_size": len(raw_json),
        }
