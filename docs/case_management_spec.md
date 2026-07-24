# 🕵️ Human-in-the-Loop Case Management & Workbench Specification

The Case Management Workbench provides fraud investigators and compliance officers with a 6-stage lifecycle for reviewing, escalating, and resolving suspicious transaction alerts.

---

## 📌 6-Stage Case Lifecycle

```
[NEW] ➔ [ASSIGNED] ➔ [UNDER_INVESTIGATION] ➔ [ESCALATED] ➔ [RESOLVED_CONFIRMED_FRAUD / RESOLVED_FALSE_POSITIVE]
```

1. **`NEW`**: Case automatically opened from single or grouped fraud alerts.
2. **`ASSIGNED`**: Assigned to a specific fraud investigator analyst (`assigned_to`).
3. **`UNDER_INVESTIGATION`**: Active review underway (KYC check, graph entity expansion, SHAP feature attribution inspection).
4. **`ESCALATED`**: Escalated to compliance officer or legal supervisor for high-value/complex cases.
5. **`RESOLVED_CONFIRMED_FRAUD`**: Terminal status confirming malicious fraud (requires Four-Eyes supervisor signature `SIG_SUPERVISOR_*`).
6. **`RESOLVED_FALSE_POSITIVE`**: Terminal status closing benign alert (requires Four-Eyes supervisor signature `SIG_SUPERVISOR_*`).

---

## 🔐 Four-Eyes Dual Authorization Rule

To satisfy SOC2 and EU AI Act Article 14 human oversight requirements:
- Resolving a case (`RESOLVED_CONFIRMED_FRAUD` or `RESOLVED_FALSE_POSITIVE`) **requires** a valid `supervisor_signature` matching format `SIG_SUPERVISOR_<ID>`.
- Any resolution attempt without supervisor signoff throws `InvalidCaseTransitionError`.
