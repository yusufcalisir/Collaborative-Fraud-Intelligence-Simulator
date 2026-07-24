# 🔄 Zero-Downtime Platform Upgrade & Client Compatibility Strategy

The Zero-Downtime Deployment Manager orchestrates rolling cluster instance updates, graceful gRPC/REST client connection draining, and 48-hour dual-version compatibility windows to eliminate downtime during platform releases.

---

## 📌 5-Stage Deployment Pipeline

```
[IDLE] ➔ [DRAINING_CONNECTIONS] ➔ [ROLLING_UPGRADE] ➔ [DUAL_VERSION_ACTIVE] ➔ [UPGRADE_COMPLETED]
```

1. **`IDLE`**: Cluster running at steady state on `current_version`.
2. **`DRAINING_CONNECTIONS`**: Active client connections are gracefully migrated to standby pods (`drain_client_connections`) without dropping active requests.
3. **`ROLLING_UPGRADE`**: Pod instances are updated batch-by-batch to `target_version`.
4. **`DUAL_VERSION_ACTIVE`**: Both old and new API versions coexist for a 48-hour deprecation grace period (`UpgradeWindow`).
5. **`UPGRADE_COMPLETED`**: Old pods are terminated and platform `current_version` is promoted.

---

## 🛡️ Client SDK Auto-Upgrade Notifications

gRPC and REST response headers include `x-cfi-deprecation-warning` and `x-cfi-target-version` to signal bank client SDKs to perform zero-downtime client-side upgrades.
