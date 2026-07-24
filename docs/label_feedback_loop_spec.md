# 🔄 Privacy-Preserving Label Feedback Loop Specification

The Label Feedback Loop connects investigator case determinations (`CONFIRMED_FRAUD` or `FALSE_POSITIVE`) back into local bank training data buffers, enabling continuous federated model retraining without compromising customer privacy or violating zero-PII constraints.

---

## 📌 Workflow Overview

1. **Local Analyst Determination**: Investigator resolves case on Workbench (`RESOLVED_CONFIRMED_FRAUD` / `RESOLVED_FALSE_POSITIVE`).
2. **Zero-PII Verification**: `LabelPrivacyGuard` verifies transaction identifier is an HMAC-SHA256 hash ($\ge 32$ hex characters) and ensures no unmasked raw PII is passed.
3. **Local Buffer Ingestion**: Ground-truth label is appended strictly to local tenant training buffer (`storage/tenant_{id}/label_buffer.json`).
4. **DP-Noise Gradient Delta**: `LocalLabelFeedbackPipeline` computes local model weight updates ($\Delta W_{local}$) with Gaussian Differential Privacy noise ($\epsilon \le 2.0$).
5. **Federated Aggregation**: DP-protected weight deltas are submitted to the Flower FL coordinator for consortium aggregation.

---

## 🛡️ Differential Privacy Bounds

- **Privacy Parameter**: $\epsilon \le 2.0$, $\delta = 10^{-5}$
- **Noise Distribution**: Gaussian noise $N(0, \sigma^2)$ where $\sigma = \frac{\Delta f \sqrt{2 \ln(1.25/\delta)}}{\epsilon}$
- **Zero-PII Guarantee**: Raw transaction records, IBANs, customer names, and account numbers never cross node boundaries.
