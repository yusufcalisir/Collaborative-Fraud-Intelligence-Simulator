# ruff: noqa: UP042
"""Domain models for Federated Consortium Governance & Membership Protocol."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ConsortiumStatus(str, Enum):
    """Status enum for a federated multi-bank consortium."""

    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    ARCHIVED = "ARCHIVED"


class ProposalStatus(str, Enum):
    """Status enum for membership or policy voting proposals."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class MemberRole(str, Enum):
    """Role enum for a member institution in a consortium."""

    FOUNDER = "FOUNDER"
    FULL_MEMBER = "FULL_MEMBER"
    OBSERVER = "OBSERVER"


class ProposalAction(str, Enum):
    """Action type for a governance proposal."""

    ADD_MEMBER = "ADD_MEMBER"
    REMOVE_MEMBER = "REMOVE_MEMBER"
    UPDATE_POLICY = "UPDATE_POLICY"


@dataclass
class ConsortiumMember:
    """Represents a member institution participating in a consortium."""

    bank_id: str
    role: MemberRole = MemberRole.FULL_MEMBER
    voting_power: float = 1.0
    joined_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class MembershipProposal:
    """Represents a voting proposal for consortium membership or policy changes."""

    proposal_id: str
    consortium_id: str
    creator_bank_id: str
    target_bank_id: str
    action: ProposalAction
    required_quorum_ratio: float = 0.51  # 51% majority required by default
    votes_for: set[str] = field(default_factory=set)
    votes_against: set[str] = field(default_factory=set)
    status: ProposalStatus = ProposalStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Consortium:
    """Domain model representing a multi-bank federated consortium."""

    consortium_id: str
    name: str
    quorum_ratio: float = 0.51  # Quorum ratio (e.g. 0.51 for 51%, 0.66 for 2/3)
    min_members_n: int = 2
    max_epsilon: float = 5.0
    status: ConsortiumStatus = ConsortiumStatus.DRAFT
    members: dict[str, ConsortiumMember] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
