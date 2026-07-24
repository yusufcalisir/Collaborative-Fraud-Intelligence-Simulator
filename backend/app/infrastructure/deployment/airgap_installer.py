# ruff: noqa: UP042, TC003
"""Air-Gapped Deployment Package Builder and Verifier."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AirGapBundleManifest:
    """Dataclass holding manifest metadata for air-gapped deployment bundle."""

    bundle_id: str
    version: str
    sha256_checksum: str
    total_files: int
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class AirGapBundleBuilder:
    """Builds self-contained air-gapped installation tarballs with cryptographic manifests."""

    def build_airgap_bundle(
        self,
        output_dir: Path,
        target_version: str = "v2.0.0",
    ) -> AirGapBundleManifest:
        """Packages self-contained offline deployment bundle with SHA-256 manifest."""
        output_dir.mkdir(parents=True, exist_ok=True)
        bundle_id = f"airgap_{uuid.uuid4().hex[:8]}"

        # Create sample offline bundle artifacts
        bundle_file = output_dir / f"cfi_airgap_{target_version}.json"
        bundle_contents = {
            "bundle_id": bundle_id,
            "version": target_version,
            "offline_wheels": ["torch-2.2.0-cp312-manylinux.whl", "fastapi-0.110.0.whl"],
            "docker_compose": "version: '3.8'\nservices:\n  cfi_backend:\n    image: cfi_backend:offline",
            "model_weights": "model_v2.0.0.pt",
        }

        content_bytes = json.dumps(bundle_contents, indent=2).encode("utf-8")
        bundle_file.write_bytes(content_bytes)

        checksum = hashlib.sha256(content_bytes).hexdigest()

        manifest = AirGapBundleManifest(
            bundle_id=bundle_id,
            version=target_version,
            sha256_checksum=checksum,
            total_files=1,
        )

        manifest_file = output_dir / "airgap_manifest.json"
        manifest_file.write_text(
            json.dumps(
                {
                    "bundle_id": manifest.bundle_id,
                    "version": manifest.version,
                    "sha256_checksum": manifest.sha256_checksum,
                    "total_files": manifest.total_files,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        logger.info(
            "Built Air-Gapped deployment bundle %s (Version: %s, SHA-256: %s)",
            bundle_id,
            target_version,
            checksum[:16],
        )
        return manifest

    def verify_airgap_bundle(self, bundle_file: Path, manifest_file: Path) -> bool:
        """Verifies SHA-256 checksum integrity of an air-gapped bundle against its manifest."""
        if not bundle_file.exists() or not manifest_file.exists():
            return False

        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
        expected_checksum = manifest_data.get("sha256_checksum")

        actual_checksum = hashlib.sha256(bundle_file.read_bytes()).hexdigest()
        is_valid = actual_checksum == expected_checksum

        if is_valid:
            logger.info("VERIFIED Air-Gapped bundle checksum: %s", actual_checksum[:16])
        else:
            logger.error(
                "CORRUPTED Air-Gapped bundle! Expected: %s, Got: %s",
                expected_checksum,
                actual_checksum,
            )

        return is_valid
