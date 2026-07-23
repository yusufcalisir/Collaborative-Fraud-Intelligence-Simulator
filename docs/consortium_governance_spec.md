# 🏛️ Federated Consortium Governance & Membership Protocol Specification

The Federated Consortium Governance engine enables multi-bank alliances (e.g. European AML Network, Nordic Fraud Defense Consortium) to establish democratic, quorum-based governance rules for collaborative fraud detection.

---

## ⚖️ Quorum Governance ($K/N$) Mechanics

1. **Democratic Voting Quorums**:
   - Member additions, node evictions, and differential privacy budget changes require a voting proposal meeting the consortium's configured quorum ratio ($K/N$, default 51% majority).
   - No single financial institution can unilaterally onboard or evict nodes without consensus.

2. **Proposal Lifecycle**:
   - `PENDING`: Open for votes from active member institutions.
   - `APPROVED`: Reached $K/N$ quorum threshold; action automatically applied to consortium state.
   - `REJECTED`: Received sufficient negative votes to prevent quorum.
   - `EXPIRED`: Proposal voting window closed without reaching quorum.

3. **Privacy Budget Caps ($\epsilon_{max}$)**:
   - Consortiums define strict upper bounds on global Differential Privacy budget expenditure ($\epsilon_{max}$) to protect participating banks against privacy leakages.

---

## 🛠️ Code Example

```python
from app.application.services.consortium_service import ConsortiumGovernanceService
from app.domain.consortium_governance import ProposalAction

service = ConsortiumGovernanceService()

# 1. Create alliance
consortium = service.create_consortium(
    consortium_id="eu_aml_network",
    name="European AML Network",
    founder_bank_id="bank_a",
    quorum_ratio=0.51,
)

# 2. Propose adding Bank B
proposal = service.propose_membership_change(
    consortium_id="eu_aml_network",
    creator_bank_id="bank_a",
    target_bank_id="bank_b",
    action=ProposalAction.ADD_MEMBER,
)
print("Proposal Status:", proposal.status)  # APPROVED (1/1 vote = 100% > 51%)
```
