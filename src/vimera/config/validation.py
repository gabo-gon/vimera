from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from .models import SimulationConfig


def validate_simulation_config(config: SimulationConfig) -> SimulationConfig:
    """
    Validate scientific constraints for a synthetic simulation.

    Pydantic validates individual fields. This function validates
    relationships between fields.
    """

    target_abundance = sum(
        target.abundance for target in config.targets
    )

    background_abundance = config.background.abundance

    total_abundance = target_abundance + background_abundance

    if total_abundance > 1:
        raise ValueError(
            "The sum of target and background abundances cannot exceed 1. "
            f"Current total: {total_abundance:.6f}"
        )
    
    if config.sequencing.platform.value == "illumina":
        if not config.sequencing.paired_end:
            # Single-end Illumina is allowed, so this is intentionally
            # not an error. This section is reserved for platform-specific
            # validation as the simulator integration is implemented.
            pass

    if config.sequencing.platform.value == "ont":
        if config.sequencing.paired_end:
            raise ValueError(
                "ONT sequencing cannot use paired-end reads."
            )

    return config


def validate_config_dict(
    config: dict[str, Any],
) -> SimulationConfig:
    """
    Validate a raw dictionary as a SimulationConfig.

    This helper is useful for tests and for the configuration loader.
    """

    try:
        config_model = SimulationConfig.model_validate(config)
    except ValidationError as exc:
        raise ValueError(
            f"Invalid VIMERA configuration:\n{exc}"
        ) from exc

    return validate_simulation_config(config_model)