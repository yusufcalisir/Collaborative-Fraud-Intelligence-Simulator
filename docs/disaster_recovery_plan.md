# 🌐 Active-Passive Multi-Region Disaster Recovery Plan

The Disaster Recovery (DR) architecture ensures continuous availability of the Federated Learning coordinator across geo-distributed cloud regions (`eu-west-1` primary, `eu-central-1` standby).

---

## 📌 RTO & RPO SLA Commitments

- **Recovery Time Objective (RTO)**: $< 30\text{ seconds}$ (Automatic failover detection and standby promotion).
- **Recovery Point Objective (RPO)**: $0\text{ records lost}$ (Synchronous Raft/PostgreSQL consensus state replication).

---

## 🔄 Automatic Failover Lifecycle

```
[Primary Region A (Active)] ──(Heartbeat Timeout >15s)──> [Demoted to PASSIVE]
                                                              │
                                                              ▼
[Standby Region B (Passive)] ────────(Promoted)─────────> [FAILOVER_PROMOTED (Active)]
```

1. **Heartbeat Monitoring**: Passive standby coordinator monitors primary region health every 5 seconds.
2. **Failure Detection**: If primary heartbeats fail for $> 15\text{s}$, `MultiRegionFailoverManager` demotes region A.
3. **Standby Promotion**: Region B coordinator is promoted to `FAILOVER_PROMOTED`.
4. **Audit Logging**: A SHA-256 signed `FailoverAuditEvent` record is appended to the immutable compliance log.
