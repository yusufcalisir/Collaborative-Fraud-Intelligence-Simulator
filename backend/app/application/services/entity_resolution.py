"""Entity resolution service.

Creates and resolves entities across institutions using deterministic
hashing. Entities represent real-world objects (customers, merchants,
devices, etc.) identified by HMAC-SHA256 hashes rather than raw PII.

The key insight: the same raw identifier at different banks produces
the same hash, enabling entity matching without exposing the underlying
private information. In production, the HMAC key would be managed by
a trusted third party or derived from MPC.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone

from app.domain.entities_phase2 import Entity, Relationship
from app.domain.enums import EntityType, RelationshipType, RiskLevel
from app.domain.value_objects_phase2 import PrivacyPreservingIdentifier

logger = logging.getLogger(__name__)


class EntityResolutionService:
    """Manages privacy-preserving entity resolution across institutions.

    Entities are identified by deterministic hashes. The same underlying
    individual at two different banks will have the same privacy_id,
    enabling cross-institution correlation without PII exposure.
    """

    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}
        self._relationships: dict[str, Relationship] = {}
        # Index: privacy_hash → list of entity IDs
        self._hash_index: dict[str, list[str]] = defaultdict(list)

    def create_entity(
        self,
        entity_type: EntityType,
        raw_identifier: str,
        bank_id: str,
        attributes: dict | None = None,
    ) -> Entity:
        """Create a privacy-preserving entity.

        The raw identifier is hashed immediately. The hash is stored,
        the raw value is discarded. The entity's display_label is a
        short, non-PII label for UI display.
        """
        privacy_id = PrivacyPreservingIdentifier.compute(raw_identifier, entity_type.value)

        # Check if we already have this entity for this bank
        existing = self._find_entity(privacy_id, bank_id)
        if existing:
            existing.last_seen = datetime.now(timezone.utc)
            return existing

        # Generate a short display label
        type_prefix = {
            EntityType.CUSTOMER: "CUST",
            EntityType.MERCHANT: "MERCH",
            EntityType.DEVICE: "DEV",
            EntityType.CARD: "CARD",
            EntityType.EMAIL: "EMAIL",
            EntityType.PHONE: "PHONE",
            EntityType.IP_ADDRESS: "IP",
        }
        prefix = type_prefix.get(entity_type, "ENT")
        display_label = f"{prefix}-{privacy_id[:6]}"

        entity = Entity(
            entity_type=entity_type,
            privacy_id=privacy_id,
            bank_id=bank_id,
            display_label=display_label,
            attributes=attributes or {},
        )

        self._entities[entity.id] = entity
        self._hash_index[privacy_id].append(entity.id)

        return entity

    def resolve_cross_institution(self, privacy_hash: str) -> list[Entity]:
        """Find matching entities across all banks.

        Returns all entities that share the same privacy hash,
        indicating they represent the same real-world entity at
        different institutions.
        """
        entity_ids = self._hash_index.get(privacy_hash, [])
        entities = [self._entities[eid] for eid in entity_ids if eid in self._entities]

        if len(entities) > 1:
            banks = set(e.bank_id for e in entities)
            logger.info(
                "Cross-institution match: hash=%s found at %d banks: %s",
                privacy_hash[:8], len(banks), banks,
            )

        return entities

    def detect_shared_entities(
        self,
        bank_a_id: str,
        bank_b_id: str,
    ) -> list[dict]:
        """Find entities that appear at both institutions.

        Returns a list of matches with the shared privacy hash and
        entity details from each bank.
        """
        bank_a_hashes = {
            e.privacy_id: e
            for e in self._entities.values()
            if e.bank_id == bank_a_id
        }
        bank_b_hashes = {
            e.privacy_id: e
            for e in self._entities.values()
            if e.bank_id == bank_b_id
        }

        shared_hashes = set(bank_a_hashes.keys()) & set(bank_b_hashes.keys())
        matches = []
        for h in shared_hashes:
            matches.append({
                "privacy_hash": h,
                "entity_type": bank_a_hashes[h].entity_type.value,
                "bank_a_entity_id": bank_a_hashes[h].id,
                "bank_b_entity_id": bank_b_hashes[h].id,
                "bank_a_risk": bank_a_hashes[h].risk_level.value,
                "bank_b_risk": bank_b_hashes[h].risk_level.value,
            })

        logger.info(
            "Found %d shared entities between %s and %s",
            len(matches), bank_a_id, bank_b_id,
        )
        return matches

    def build_entity_profile(self, entity_id: str) -> dict:
        """Build a risk profile for an entity.

        Aggregates alert count, relationship count, cross-institution
        presence, and risk factors.
        """
        entity = self._entities.get(entity_id)
        if not entity:
            raise ValueError(f"Entity not found: {entity_id}")

        # Find all related entities via relationships
        relationships = [
            r for r in self._relationships.values()
            if r.source_entity_id == entity_id or r.target_entity_id == entity_id
        ]

        # Cross-institution presence
        cross_matches = self.resolve_cross_institution(entity.privacy_id)
        banks_present = list(set(e.bank_id for e in cross_matches))

        return {
            "entity_id": entity.id,
            "entity_type": entity.entity_type.value,
            "privacy_id": entity.privacy_id,
            "display_label": entity.display_label,
            "bank_id": entity.bank_id,
            "risk_level": entity.risk_level.value,
            "alert_count": entity.alert_count,
            "relationship_count": len(relationships),
            "cross_institution_count": len(banks_present),
            "banks_present": banks_present,
            "first_seen": entity.first_seen.isoformat(),
            "last_seen": entity.last_seen.isoformat(),
            "attributes": entity.attributes,
        }

    def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: RelationshipType,
        confidence: float = 1.0,
        evidence: list[str] | None = None,
    ) -> Relationship:
        """Create a relationship between two entities."""
        rel = Relationship(
            source_entity_id=source_id,
            target_entity_id=target_id,
            relationship_type=relationship_type,
            confidence=confidence,
            evidence=evidence or [],
        )
        self._relationships[rel.id] = rel
        return rel

    def update_risk_level(self, entity_id: str, risk_level: RiskLevel) -> None:
        entity = self._entities.get(entity_id)
        if entity:
            entity.risk_level = risk_level

    def increment_alert_count(self, entity_id: str) -> None:
        entity = self._entities.get(entity_id)
        if entity:
            entity.alert_count += 1

    def get_entity(self, entity_id: str) -> Entity | None:
        return self._entities.get(entity_id)

    def get_entities(
        self,
        entity_type: EntityType | None = None,
        bank_id: str | None = None,
        risk_level: RiskLevel | None = None,
        limit: int = 50,
    ) -> list[Entity]:
        entities = list(self._entities.values())
        if entity_type:
            entities = [e for e in entities if e.entity_type == entity_type]
        if bank_id:
            entities = [e for e in entities if e.bank_id == bank_id]
        if risk_level:
            entities = [e for e in entities if e.risk_level == risk_level]
        return sorted(entities, key=lambda e: e.alert_count, reverse=True)[:limit]

    def get_relationships(self) -> list[Relationship]:
        return list(self._relationships.values())

    # ── Private helpers ────────────────────────

    def _find_entity(self, privacy_id: str, bank_id: str) -> Entity | None:
        entity_ids = self._hash_index.get(privacy_id, [])
        for eid in entity_ids:
            entity = self._entities.get(eid)
            if entity and entity.bank_id == bank_id:
                return entity
        return None
