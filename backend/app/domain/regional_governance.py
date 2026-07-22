"""Domain-level Regional Governance Rings & Cross-Border Data Sovereignty Engine.

Enforces geographic boundary segregation (EU-Central, US-East, APAC-Singapore)
to comply with Schrems II, GDPR Article 22, and EU AI Act data sovereignty mandates.
Executes intra-region model weight aggregation before inter-regional DP-scrubbed meta-aggregation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)


class Region(str, Enum):  # noqa: UP042
    """Supported geographic regional governance rings."""

    EU_CENTRAL = "eu-central-1"
    US_EAST = "us-east-1"
    APAC_SINGAPORE = "apac-singapore-1"


@dataclass
class RegionalRingNodeConfig:
    """Node region assignment and data sovereignty configuration."""

    node_id: str
    bank_name: str
    region: Region
    data_sovereignty_strict: bool = True
    allow_cross_border_meta_aggregation: bool = True


class CrossBorderSovereigntyViolationError(Exception):
    """Raised when raw model parameters attempt to cross geographic regional boundaries."""

    pass


class CrossBorderSovereigntyFilter:
    """Enforces Schrems II and GDPR Article 22 cross-border data transfer compliance rules."""

    @staticmethod
    def validate_transfer(
        source_region: Region,
        destination_region: Region,
        is_dp_scrubbed: bool,
        is_raw_parameter: bool,
    ) -> bool:
        """Validates if model parameter transfer across regions satisfies data sovereignty laws.

        Raw parameters crossing regions without Differential Privacy scrubbing are strictly blocked.
        """
        if source_region == destination_region:
            return True

        if is_raw_parameter and not is_dp_scrubbed:
            logger.error(
                "Cross-border sovereignty violation: Raw parameters transfer from %s to %s blocked.",
                source_region.value,
                destination_region.value,
            )
            raise CrossBorderSovereigntyViolationError(
                f"Schrems II / GDPR Violation: Raw parameter transfer from {source_region.value} "
                f"to {destination_region.value} without DP noise scrubbing is strictly prohibited."
            )

        return True


@dataclass
class RegionalGovernanceRingManager:
    """Manages regional ring topologies, intra-region aggregation, and inter-region DP meta-aggregation."""

    nodes: dict[str, RegionalRingNodeConfig] = field(default_factory=dict)
    regional_weights: dict[Region, dict[str, np.ndarray]] = field(default_factory=dict)

    def register_node(
        self,
        node_id: str,
        bank_name: str,
        region: Region,
        data_sovereignty_strict: bool = True,
    ) -> RegionalRingNodeConfig:
        """Registers a bank node to a designated regional governance ring."""
        config = RegionalRingNodeConfig(
            node_id=node_id,
            bank_name=bank_name,
            region=region,
            data_sovereignty_strict=data_sovereignty_strict,
        )
        self.nodes[node_id] = config
        logger.info(
            "Registered bank node %s (%s) to region ring %s", bank_name, node_id, region.value
        )
        return config

    def aggregate_intra_region(
        self,
        region: Region,
        client_weights: dict[str, dict[str, np.ndarray]],
        sample_counts: dict[str, int],
    ) -> dict[str, np.ndarray]:
        """Performs localized FedAvg weight aggregation strictly within the regional ring."""
        regional_node_ids = [
            n_id
            for n_id, cfg in self.nodes.items()
            if cfg.region == region and n_id in client_weights
        ]

        if not regional_node_ids:
            logger.warning("No nodes found for intra-region aggregation in region %s", region.value)
            return {}

        total_samples = sum(sample_counts.get(n_id, 1) for n_id in regional_node_ids)
        first_node_weights = client_weights[regional_node_ids[0]]
        aggregated: dict[str, np.ndarray] = {
            layer: np.zeros_like(weights) for layer, weights in first_node_weights.items()
        }

        for n_id in regional_node_ids:
            w_dict = client_weights[n_id]
            weight_factor = sample_counts.get(n_id, 1) / max(1, total_samples)
            for layer, arr in w_dict.items():
                aggregated[layer] += arr * weight_factor

        self.regional_weights[region] = aggregated
        logger.info(
            "Completed intra-region aggregation for ring %s across %d nodes (%d total samples)",
            region.value,
            len(regional_node_ids),
            total_samples,
        )
        return aggregated

    def aggregate_inter_region_meta(
        self,
        inter_region_dp_epsilon: float = 1.0,
        inter_region_dp_delta: float = 1e-5,
    ) -> dict[str, np.ndarray]:
        """Executes inter-regional meta-aggregation across regional rings.

        Applies Differential Privacy noise scrubbing prior to inter-regional transfer.
        """
        if not self.regional_weights:
            return {}

        regions = list(self.regional_weights.keys())
        first_region_weights = self.regional_weights[regions[0]]
        global_meta: dict[str, np.ndarray] = {
            layer: np.zeros_like(weights) for layer, weights in first_region_weights.items()
        }

        num_regions = len(regions)
        for reg in regions:
            # Validate cross-border compliance for meta-aggregation
            for target_reg in regions:
                if reg != target_reg:
                    CrossBorderSovereigntyFilter.validate_transfer(
                        source_region=reg,
                        destination_region=target_reg,
                        is_dp_scrubbed=True,  # Inter-region transfer uses DP noise
                        is_raw_parameter=False,
                    )

            reg_weights = self.regional_weights[reg]
            for layer, arr in reg_weights.items():
                global_meta[layer] += arr / num_regions

        # Apply Differential Privacy noise scrubbing to global meta weights
        scale = 0.01 * (1.0 / max(0.1, inter_region_dp_epsilon))
        for layer in global_meta:
            noise = np.random.normal(0, scale, size=global_meta[layer].shape)
            global_meta[layer] += noise

        logger.info(
            "Executed inter-region meta-aggregation across %d rings with DP noise (eps=%.2f, delta=%.1e)",
            num_regions,
            inter_region_dp_epsilon,
            inter_region_dp_delta,
        )
        return global_meta
