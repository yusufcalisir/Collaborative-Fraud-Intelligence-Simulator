"""Consortium Governance Service handling multi-bank alliances and voting quorums."""

from __future__ import annotations

import logging
import uuid

from app.domain.consortium_governance import (
    Consortium,
    ConsortiumMember,
    ConsortiumStatus,
    MemberRole,
    MembershipProposal,
    ProposalAction,
    ProposalStatus,
)

logger = logging.getLogger(__name__)


class ConsortiumGovernanceService:
    """Manages consortium creation, voting proposals, and member lifecycle."""

    def __init__(self) -> None:
        self._consortia: dict[str, Consortium] = {}
        self._proposals: dict[str, MembershipProposal] = {}

    def create_consortium(
        self,
        consortium_id: str,
        name: str,
        founder_bank_id: str,
        quorum_ratio: float = 0.51,
        max_epsilon: float = 5.0,
    ) -> Consortium:
        """Initializes a new multi-bank consortium with founder member."""
        clean_id = consortium_id.lower().strip()
        if clean_id in self._consortia:
            return self._consortia[clean_id]

        founder = ConsortiumMember(bank_id=founder_bank_id, role=MemberRole.FOUNDER)
        consortium = Consortium(
            consortium_id=clean_id,
            name=name,
            quorum_ratio=quorum_ratio,
            max_epsilon=max_epsilon,
            status=ConsortiumStatus.ACTIVE,
            members={founder_bank_id: founder},
        )

        self._consortia[clean_id] = consortium
        logger.info(
            "Created consortium '%s' (%s) with founder '%s'", name, clean_id, founder_bank_id
        )
        return consortium

    def propose_membership_change(
        self,
        consortium_id: str,
        creator_bank_id: str,
        target_bank_id: str,
        action: ProposalAction = ProposalAction.ADD_MEMBER,
    ) -> MembershipProposal:
        """Creates a membership voting proposal (e.g. ADD_MEMBER or REMOVE_MEMBER)."""
        clean_id = consortium_id.lower().strip()
        if clean_id not in self._consortia:
            raise KeyError(f"Consortium '{clean_id}' does not exist.")

        consortium = self._consortia[clean_id]
        if creator_bank_id not in consortium.members:
            raise ValueError(
                f"Bank '{creator_bank_id}' is not a member of consortium '{clean_id}'."
            )

        proposal_id = f"prop_{uuid.uuid4().hex[:8]}"
        proposal = MembershipProposal(
            proposal_id=proposal_id,
            consortium_id=clean_id,
            creator_bank_id=creator_bank_id,
            target_bank_id=target_bank_id,
            action=action,
            required_quorum_ratio=consortium.quorum_ratio,
        )

        # Creator automatically votes FOR the proposal
        proposal.votes_for.add(creator_bank_id)
        self._proposals[proposal_id] = proposal

        logger.info(
            "Opened governance proposal %s in consortium %s for bank %s",
            proposal_id,
            clean_id,
            target_bank_id,
        )
        self._evaluate_proposal_quorum(proposal)
        return proposal

    def cast_vote(self, proposal_id: str, bank_id: str, approve: bool) -> MembershipProposal:
        """Casts a vote FOR or AGAINST an active proposal."""
        if proposal_id not in self._proposals:
            raise KeyError(f"Proposal '{proposal_id}' does not exist.")

        proposal = self._proposals[proposal_id]
        consortium = self._consortia[proposal.consortium_id]

        if bank_id not in consortium.members:
            raise ValueError(
                f"Bank '{bank_id}' is not a member of consortium '{proposal.consortium_id}'."
            )

        if proposal.status != ProposalStatus.PENDING:
            raise ValueError(f"Proposal '{proposal_id}' is already {proposal.status.value}.")

        if approve:
            proposal.votes_for.add(bank_id)
            proposal.votes_against.discard(bank_id)
        else:
            proposal.votes_against.add(bank_id)
            proposal.votes_for.discard(bank_id)

        logger.info(
            "Bank %s voted %s on proposal %s", bank_id, "FOR" if approve else "AGAINST", proposal_id
        )
        self._evaluate_proposal_quorum(proposal)
        return proposal

    def _evaluate_proposal_quorum(self, proposal: MembershipProposal) -> None:
        """Evaluates voting quorum ($K/N$) ratio and executes proposal action if passed."""
        consortium = self._consortia[proposal.consortium_id]
        total_members = max(len(consortium.members), 1)

        ratio_for = len(proposal.votes_for) / total_members
        ratio_against = len(proposal.votes_against) / total_members

        if ratio_for >= proposal.required_quorum_ratio:
            proposal.status = ProposalStatus.APPROVED
            self._execute_proposal_action(proposal)
            logger.info("Proposal %s APPROVED with ratio %.2f", proposal.proposal_id, ratio_for)
        elif ratio_against > (1.0 - proposal.required_quorum_ratio):
            proposal.status = ProposalStatus.REJECTED
            logger.info("Proposal %s REJECTED", proposal.proposal_id)

    def _execute_proposal_action(self, proposal: MembershipProposal) -> None:
        """Applies approved proposal actions to consortium state."""
        consortium = self._consortia[proposal.consortium_id]
        target = proposal.target_bank_id

        if proposal.action == ProposalAction.ADD_MEMBER and target not in consortium.members:
            consortium.members[target] = ConsortiumMember(
                bank_id=target, role=MemberRole.FULL_MEMBER
            )
            logger.info("Bank %s joined consortium %s", target, consortium.consortium_id)
        elif proposal.action == ProposalAction.REMOVE_MEMBER and target in consortium.members:
            del consortium.members[target]
            logger.info("Bank %s evicted from consortium %s", target, consortium.consortium_id)

    def get_consortium(self, consortium_id: str) -> Consortium | None:
        """Retrieves consortium by ID."""
        return self._consortia.get(consortium_id.lower().strip())
