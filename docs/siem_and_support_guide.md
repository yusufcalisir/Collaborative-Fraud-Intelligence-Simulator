# 📊 SIEM Integration & Support Diagnostic Bundle Guide

The SIEM Log Exporter (`SIEMLogExporter`) formats security audit events into Syslog Common Event Format (CEF) and JSON for Splunk and Datadog ingestion, while the Support Diagnostic Compiler (`SupportDiagnosticCompiler`) packages PII-redacted telemetry bundles for customer support.

---

## 📌 SIEM Log Forwarding Formats

### 1. Common Event Format (CEF) Syslog

```syslog
CEF:0|CFI|Simulator|2.0|ALERT_CREATED|High risk fraud transaction detected|10|eventId=evt_1001 srcBank=bank_alpha rt=2026-07-24T14:00:00Z
```

### 2. Splunk HEC Payload

```json
{
  "event": {
    "event_id": "evt_1001",
    "event_type": "ALERT_CREATED",
    "message": "High risk fraud transaction detected",
    "bank": "bank_alpha"
  },
  "sourcetype": "cfi:audit:json",
  "source": "cfi_simulator"
}
```

---

## 🩺 Support Telemetry Bundle Sanitization

The `SupportDiagnosticCompiler` automatically scans log text and redacts sensitive PII (emails, IBANs, customer account numbers) using `[REDACTED]` before generating the SHA-256 signed diagnostic bundle.
