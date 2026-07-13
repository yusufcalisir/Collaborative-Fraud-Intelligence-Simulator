"""Unit tests for DH-PSI service."""

from __future__ import annotations

import pytest

from app.application.services.entity_resolution import EntityResolutionService
from app.application.services.psi_service import PSIService
from app.domain.enums import EntityType


@pytest.fixture
def entity_service() -> EntityResolutionService:
    return EntityResolutionService()


@pytest.fixture
def psi_service(entity_service: EntityResolutionService) -> PSIService:
    return PSIService(entity_service)


class TestPSIService:
    def test_psi_no_entities_returns_empty(self, psi_service: PSIService) -> None:
        result = psi_service.run_psi("bank_a", "bank_b", EntityType.CUSTOMER)
        assert result["matches"] == []
        assert result["stats"]["num_entities_a"] == 0
        assert result["stats"]["num_entities_b"] == 0
        assert result["stats"]["data_exchanged_bytes"] == 0

    def test_psi_matches_common_entities(
        self,
        entity_service: EntityResolutionService,
        psi_service: PSIService,
    ) -> None:
        # Create common entities
        entity_service.create_entity(
            entity_type=EntityType.CUSTOMER,
            raw_identifier="common.user@mail.com",
            bank_id="bank_a",
        )
        entity_service.create_entity(
            entity_type=EntityType.CUSTOMER,
            raw_identifier="common.user@mail.com",
            bank_id="bank_b",
        )

        # Create distinct entities
        entity_service.create_entity(
            entity_type=EntityType.CUSTOMER,
            raw_identifier="only.a@mail.com",
            bank_id="bank_a",
        )
        entity_service.create_entity(
            entity_type=EntityType.CUSTOMER,
            raw_identifier="only.b@mail.com",
            bank_id="bank_b",
        )

        # Run PSI
        result = psi_service.run_psi("bank_a", "bank_b", EntityType.CUSTOMER)
        matches = result["matches"]
        stats = result["stats"]

        assert len(matches) == 1
        assert matches[0]["entity_type"] == "customer"
        assert matches[0]["display_label_a"].startswith("CUST-")
        assert matches[0]["display_label_b"].startswith("CUST-")
        assert stats["num_entities_a"] == 2
        assert stats["num_entities_b"] == 2
        # Data exchanged = 2 * (len_a + len_b) * 64 bytes = 2 * 4 * 64 = 512 bytes
        assert stats["data_exchanged_bytes"] == 512
