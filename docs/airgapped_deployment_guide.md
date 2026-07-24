# 🔒 Air-Gapped Banking Data Center Deployment Guide

The Air-Gapped Deployment Package Builder (`AirGapBundleBuilder`) generates self-contained, zero-internet installation bundles for isolated bank data centers, protected at the edge by the Perimeter WAF Guard (`PerimeterWAFGuard`).

---

## 📌 Air-Gapped Bundle Verification & Installation

1. **Copy Bundle**: Transfer `cfi_airgap_v2.0.0.json` and `airgap_manifest.json` via secure encrypted USB/media into the air-gapped environment.
2. **Verify SHA-256 Checksum**:
   ```python
   from app.infrastructure.deployment.airgap_installer import AirGapBundleBuilder
   builder = AirGapBundleBuilder()
   valid = builder.verify_airgap_bundle(bundle_file, manifest_file)
   assert valid is True
   ```
3. **Execute Offline Docker Deployment**:
   ```bash
   docker load -i cfi_backend_offline.tar
   docker compose -f docker-compose.airgap.yml up -d
   ```
