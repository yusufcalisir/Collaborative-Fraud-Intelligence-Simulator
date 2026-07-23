# ruff: noqa: E402
"""Unit test suite for Federated Consortium Governance & Membership Protocol."""

from __future__ import annotations

from app.application.services.consortium_service import ConsortiumGovernanceService
from app.domain.consortium_governance import (
    ConsortiumStatus,
    MemberRole,
    ProposalAction,
    ProposalStatus,
)


def test_consortium_creation_and_founder() -> None:
    """Test creating a new consortium with founder member."""
    service = ConsortiumGovernanceService()
    consortium = service.create_consortium(
        consortium_id="eu_aml",
        name="European AML Network",
        founder_bank_id="bank_a",
        quorum_ratio=0.51,
        max_epsilon=4.0,
    )

    assert consortium.consortium_id == "eu_aml"
    assert consortium.name == "European AML Network"
    assert consortium.status == ConsortiumStatus.ACTIVE
    assert "bank_a" in consortium.members
    assert consortium.members["bank_a"].role == MemberRole.FOUNDER


def test_proposal_voting_quorum_approval() -> None:
    """Test membership proposal voting and automatic approval upon reaching quorum."""
    service = ConsortiumGovernanceService()
    service.create_consortium(
        consortium_id="nordic_fraud",
        name="Nordic Fraud Defense",
        founder_bank_id="bank_a",
        quorum_ratio=0.51,
    )

    # 1. Proposal created by bank_a automatically votes FOR (1/1 member = 100% > 51%)
    proposal = service.propose_membership_change(
        consortium_id="nordic_fraud",
        creator_bank_id="bank_a",
        target_bank_id="bank_b",
        action=ProposalAction.ADD_MEMBER,
    )

    assert proposal.status == ProposalStatus.APPROVED
    consortium = service.get_consortium("nordic_fraud")
    assert consortium is not None
    assert "bank_b" in consortium.members
    assert consortium.members["bank_b"].role == MemberRole.FULL_MEMBER


def test_multi_member_voting_and_eviction() -> None:
    """Test voting across multiple member banks and member eviction proposal."""
    service = ConsortiumGovernanceService()
    service.create_consortium(
        consortium_id="alliance_99",
        name="Alliance 99",
        founder_bank_id="bank_a",
        quorum_ratio=0.66,  # 2/3 majority
    )

    consortium = service.get_consortium("alliance_99")
    assert consortium is not None

    # Add bank_b (1/1 = 100% >= 66% -> APPROVED)
    prop_b = service.propose_membership_change(
        consortium_id="alliance_99",
        creator_bank_id="bank_a",
        target_bank_id="bank_b",
        action=ProposalAction.ADD_MEMBER,
    )
    assert prop_b.status == ProposalStatus.APPROVED

    # Add bank_c (bank_a proposes -> 1/2 = 50% < 66% -> PENDING)
    prop_c = service.propose_membership_change(
        consortium_id="alliance_99",
        creator_bank_id="bank_a",
        target_bank_id="bank_c",
        action=ProposalAction.ADD_MEMBER,
    )
    assert prop_c.status == ProposalStatus.PENDING

    # bank_b votes FOR -> 2/2 = 100% >= 66% -> APPROVED
    service.cast_vote(prop_c.proposal_id, "bank_b", approve=True)
    assert prop_c.status == ProposalStatus.APPROVED
    assert len(consortium.members) == 3

    # Propose evicting bank_c (bank_a proposes -> 1/3 = 33% < 66% -> PENDING)
    evict_prop = service.propose_membership_change(
        consortium_id="alliance_99",
        creator_bank_id="bank_a",
        target_bank_id="bank_c",
        action=ProposalAction.REMOVE_MEMBER,
    )
    assert evict_prop.status == ProposalStatus.PENDING

    # Bank B votes FOR -> 2/3 = 66.6% >= 66% -> APPROVED
    service.cast_vote(evict_prop.proposal_id, "bank_b", approve=True)
    assert evict_prop.status == ProposalStatus.APPROVED
    assert "bank_c" not in consortium.members
