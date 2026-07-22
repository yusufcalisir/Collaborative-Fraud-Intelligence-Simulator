"""MinHash Locality-Sensitive Hashing (LSH) Fuzzy PSI Domain Module.

Enables privacy-preserving fuzzy entity matching across bank perimeters
using character 3-gram MinHash signatures and LSH band bucket partitioning.
Raw customer PII (names, addresses, phone numbers) is never transmitted.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


def compute_minhash_signature(text: str, num_hashes: int = 16) -> list[int]:
    """Computes character 3-gram MinHash signature vector for input text."""
    if not text:
        return [0] * num_hashes

    clean_text = text.lower().strip()
    shingles = (
        {clean_text}
        if len(clean_text) < 3
        else {clean_text[i : i + 3] for i in range(len(clean_text) - 2)}
    )

    signature = []
    for i in range(num_hashes):
        min_val = float("inf")
        for shingle in shingles:
            h_str = f"{shingle}:{i}"
            h_val = int(hashlib.sha256(h_str.encode("utf-8")).hexdigest(), 16)
            if h_val < min_val:
                min_val = h_val
        signature.append(int(min_val % 1000000))

    return signature


def calculate_jaccard_similarity(sig1: list[int], sig2: list[int]) -> float:
    """Estimates Jaccard similarity between two MinHash signature vectors."""
    if not sig1 or not sig2 or len(sig1) != len(sig2):
        return 0.0
    matches = sum(1 for x, y in zip(sig1, sig2) if x == y)
    return matches / len(sig1)


def lsh_band_buckets(signature: list[int], num_bands: int = 16) -> list[str]:
    """Partitions a MinHash signature into LSH band hashes for candidate indexing.

    Args:
        signature: MinHash signature vector of length N (e.g., 16).
        num_bands: Number of bands (default 16, 1 element per band for high recall candidate retrieval).

    Returns:
        List of SHA-256 band hashes suitable for exact bucket lookup.
    """
    if not signature:
        return []

    band_hashes = []
    for idx, val in enumerate(signature[:num_bands]):
        band_repr = f"b{idx}:{val}"
        band_hash = hashlib.sha256(band_repr.encode("utf-8")).hexdigest()[:16]
        band_hashes.append(band_hash)

    return band_hashes


@dataclass
class FuzzyMatchCandidate:
    """Represents a matched fuzzy entity candidate pair."""

    entity_id_a: str
    entity_id_b: str
    jaccard_similarity: float
    matched_bands: int
    is_match: bool


@dataclass
class FuzzyPSIMatcher:
    """Locality-Sensitive Hashing (LSH) fuzzy matcher for privacy-preserving profile matching."""

    num_hashes: int = 16
    num_bands: int = 8
    similarity_threshold: float = 0.25
    index: dict[str, list[tuple[str, str, list[int]]]] = field(default_factory=dict)

    def index_entity(self, entity_id: str, bank_id: str, raw_text: str) -> list[str]:
        """Indexes an entity profile by computing MinHash signature and LSH band buckets."""
        sig = compute_minhash_signature(raw_text, num_hashes=self.num_hashes)
        bands = lsh_band_buckets(sig, num_bands=self.num_bands)

        for band_hash in bands:
            if band_hash not in self.index:
                self.index[band_hash] = []
            self.index[band_hash].append((entity_id, bank_id, sig))

        return bands

    def match_profile(
        self, entity_id: str, bank_id: str, raw_text: str
    ) -> list[FuzzyMatchCandidate]:
        """Finds cross-bank candidate matches exceeding similarity threshold using LSH bucket lookup."""
        sig = compute_minhash_signature(raw_text, num_hashes=self.num_hashes)
        bands = lsh_band_buckets(sig, num_bands=self.num_bands)

        candidate_sigs: dict[str, tuple[list[int], int]] = {}
        for band_hash in bands:
            for cand_id, cand_bank, cand_sig in self.index.get(band_hash, []):
                if cand_bank != bank_id:
                    cnt = candidate_sigs.get(cand_id, (cand_sig, 0))[1] + 1
                    candidate_sigs[cand_id] = (cand_sig, cnt)

        results = []
        for cand_id, (cand_sig, matched_bands) in candidate_sigs.items():
            jaccard_sim = calculate_jaccard_similarity(sig, cand_sig)
            if jaccard_sim >= self.similarity_threshold:
                results.append(
                    FuzzyMatchCandidate(
                        entity_id_a=entity_id,
                        entity_id_b=cand_id,
                        jaccard_similarity=round(jaccard_sim, 4),
                        matched_bands=matched_bands,
                        is_match=True,
                    )
                )

        return sorted(results, key=lambda c: c.jaccard_similarity, reverse=True)
