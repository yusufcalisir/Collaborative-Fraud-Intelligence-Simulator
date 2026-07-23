# 🔄 Protocol Versioning & Client Compatibility Matrix Specification

This document defines the semantic versioning scheme, gRPC header handshake protocol, and backward compatibility rules for the Collaborative Fraud Intelligence platform.

---

## 📌 Protocol Versioning Scheme

Protocol releases follow **Semantic Versioning (SemVer 2.0.0)** (`MAJOR.MINOR.PATCH`):
- **MAJOR**: Breaking changes to protobuf wire formats (`fl_service.proto`), parameter serialization schemas, or cryptographic primitives (e.g. `v1.x` to `v2.x`).
- **MINOR**: Backward-compatible feature additions (e.g. new optional telemetry fields, updated drift metrics).
- **PATCH**: Backward-compatible bug fixes and performance optimizations.

---

## 📑 Platform Compatibility Matrix

| Platform Version | gRPC Protocol Version | Supported Client Range | Schema Digest Hash | Deprecation Date |
| :--- | :--- | :--- | :--- | :--- |
| **v1.0.0** | `1.0.0` | `1.0.0 - 1.99.99` | `a1b2c3d4...` | Active |
| **v1.1.0** | `1.1.0` | `1.0.0 - 1.99.99` | `e5f6g7h8...` | Active |
| **v2.0.0 (Planned)** | `2.0.0` | `2.0.0 - 2.99.99` | `99887766...` | Planned |

---

## 🤝 gRPC Header Handshake

Clients present protocol metadata in every gRPC request context:
- `x-cfi-protocol-version`: Semver string (e.g. `1.1.0`).
- `x-cfi-schema-hash`: SHA-256 digest of client feature schema.

### Rejection Status Codes
If the client version is incompatible:
- **`OUT_OF_RANGE`**: Client version is below minimum supported version or exceeds max supported version.
- **`UNIMPLEMENTED`**: Client major version does not match server major release.
