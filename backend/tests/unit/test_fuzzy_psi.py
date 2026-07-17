from app.application.services.entity_resolution import EntityResolutionService
from app.application.services.psi_service import PSIService
from app.domain.enums import EntityType
from app.domain.value_objects_phase2 import (
    calculate_jaccard_similarity,
    compute_minhash_signature,
    standardize_input,
)


def test_standardization_pipeline() -> None:
    # Names standardization: lowercase, strip accents, remove non-alphanumeric except space, normalize spaces
    assert standardize_input("Yusuf Çalışır", "customer") == "yusuf calisir"
    assert standardize_input("  François   Mitterrand  ", "merchant") == "francois mitterrand"

    # Phone standardization: keep +, strip non-digits
    assert standardize_input("+1 (555) 123-4567", "phone") == "+15551234567"
    assert standardize_input("0532-123-45-67", "phone") == "05321234567"

    # Email standardization: lowercase, remove space
    assert standardize_input(" USER.Name @Mail.com  ", "email") == "user.name@mail.com"

    # Other entity types fallback to lowercase and strip
    assert standardize_input("  some_value  ", "device") == "some_value"


def test_minhash_lsh() -> None:
    # Strings that are spelling variants should have high Jaccard similarity
    sig1 = compute_minhash_signature(standardize_input("yusuf calisir", "customer"))
    sig2 = compute_minhash_signature(standardize_input("yusuf calisir", "customer"))
    sig3 = compute_minhash_signature(standardize_input("yusuf çalışır", "customer"))
    sig4 = compute_minhash_signature(standardize_input("alexander hamilton", "customer"))

    # Identical standard forms must match 100%
    assert calculate_jaccard_similarity(sig1, sig2) == 1.0
    assert calculate_jaccard_similarity(sig1, sig3) == 1.0

    # Completely different strings should have very low/zero similarity
    assert calculate_jaccard_similarity(sig1, sig4) < 0.2


def test_fuzzy_psi_protocol() -> None:
    entity_service = EntityResolutionService()
    psi_service = PSIService(entity_service)

    # Clean the store first to ensure clean test
    entity_service._entities.clear()
    entity_service._hash_index.clear()
    entity_service._relationships.clear()

    # Create customer at Bank A
    entity_service.create_entity(
        entity_type=EntityType.CUSTOMER,
        raw_identifier="Yusuf Calisir",
        bank_id="bank_a",
        attributes={
            "phone": "+15559998888",
            "email": "yusuf@example.com",
            "device_id": "device_123",
            "birthdate": "1990-01-01",
            "surname": "Calisir",
        },
    )

    # Create matching customer at Bank B (matching 4 out of 5 attributes: phone, email, device, surname. Birthdate is different.)
    entity_service.create_entity(
        entity_type=EntityType.CUSTOMER,
        raw_identifier="Yusuf Çalışır",  # standardize_input resolves this to yusuf calisir
        bank_id="bank_b",
        attributes={
            "phone": "+1 (555) 999-8888",  # Phone will be standardized to match
            "email": "yusuf@example.com",
            "device_id": "device_123",
            "birthdate": "1995-12-12",  # Different birthdate
            "surname": "Calisir",
        },
    )

    # Run Fuzzy PSI with threshold = 3
    result = psi_service.run_psi(
        bank_a_id="bank_a",
        bank_b_id="bank_b",
        entity_type=EntityType.CUSTOMER,
        enable_fuzzy=True,
        fuzzy_threshold=3,
    )

    matches = result["matches"]
    assert len(matches) == 1
    assert matches[0]["matched_attributes"] == ["phone", "email", "device_id", "surname"]
    assert matches[0]["similarity_score"] == 0.8  # 4 out of 5 matched

    # Run with threshold = 5 (should not match because birthdate is different)
    result_strict = psi_service.run_psi(
        bank_a_id="bank_a",
        bank_b_id="bank_b",
        entity_type=EntityType.CUSTOMER,
        enable_fuzzy=True,
        fuzzy_threshold=5,
    )
    assert len(result_strict["matches"]) == 0
