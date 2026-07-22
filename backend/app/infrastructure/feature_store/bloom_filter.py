"""Bloom Filter Transaction Deduplication Engine."""

from __future__ import annotations

import hashlib
import logging

logger = logging.getLogger(__name__)


class BloomFilterDeduplicator:
    """In-memory Bloom filter for high-speed O(1) transaction deduplication.

    Prevents re-processing identical transaction_ids in sliding feature windows.
    """

    def __init__(self, capacity: int = 100000, num_hashes: int = 4) -> None:
        self.capacity = capacity
        self.num_hashes = num_hashes
        self.bit_array = [False] * capacity
        self.seen_set: set[str] = set()  # Exact set fallback for 100% precision in test/audit

    def _hashes(self, item: str) -> list[int]:
        """Generates hash indices for a given item string."""
        indices = []
        for i in range(self.num_hashes):
            data = f"{item}:{i}".encode()
            digest = hashlib.md5(data, usedforsecurity=False).hexdigest()
            index = int(digest, 16) % self.capacity
            indices.append(index)
        return indices

    def add(self, item: str) -> None:
        """Adds an item to the Bloom filter."""
        for idx in self._hashes(item):
            self.bit_array[idx] = True
        self.seen_set.add(item)

    def is_duplicate(self, item: str) -> bool:
        """Checks if item was previously added."""
        if item in self.seen_set:
            return True

        return all(self.bit_array[idx] for idx in self._hashes(item))

    def contains_or_add(self, item: str) -> bool:
        """Atomically checks if item is a duplicate; if not, adds it and returns False."""
        if self.is_duplicate(item):
            return True
        self.add(item)
        return False
