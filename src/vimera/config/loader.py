from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from .defaults import DEFAULTS
from .models import SimulationConfig
from .validation import validate_simulation_config


def load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML configuration file."""

    if not path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {path}"
        )

    if not path.is_file():
        raise ValueError(
            f"Configuration path is not a file: {path}"
        )

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if data is None:
        return {}

    if not isinstance(data, dict):
        raise ValueError(
            "The YAML configuration must contain a mapping/object "
            "at the top level."
        )

    return data


def deep_merge(
    base: dict[str, Any],
    override: dict[str, Any],
) -> dict[str, Any]:
    """
    Recursively merge two dictionaries.

    Values in ``override`` take precedence over values in ``base``.

    Nested dictionaries are merged recursively. Lists and scalar values
    are replaced completely.

    Examples
    --------
    >>> deep_merge(
    ...     {"sequencing": {"platform": "illumina", "reads": 1000}},
    ...     {"sequencing": {"reads": 5000}},
    ... )
    {'sequencing': {'platform': 'illumina', 'reads': 5000}}

    >>> deep_merge(
    ...     {"targets": [{"taxid": 1}]},
    ...     {"targets": [{"taxid": 2}]},
    ... )
    {'targets': [{'taxid': 2}]}
    """

    result = deepcopy(base)

    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(
                result[key],
                value,
            )
        else:
            # Lists are deliberately replaced rather than merged.
            result[key] = deepcopy(value)

    return result


def remove_none_values(
    data: dict[str, Any],
) -> dict[str, Any]:
    """
    Remove ``None`` values recursively.

    This prevents an omitted CLI option from overriding a value
    supplied by YAML or defaults.
    """

    cleaned: dict[str, Any] = {}

    for key, value in data.items():
        if value is None:
            continue

        if isinstance(value, dict):
            nested = remove_none_values(value)

            if nested:
                cleaned[key] = nested
        else:
            cleaned[key] = value

    return cleaned


def parse_comma_separated(
    value: str,
) -> list[str]:
    """Convert a comma-separated CLI value into a list."""

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


def parse_taxids(
    value: str,
) -> list[int]:
    """Parse comma-separated TaxIDs."""

    try:
        taxids = [
            int(item)
            for item in parse_comma_separated(value)
        ]
    except ValueError as exc:
        raise ValueError(
            f"Invalid TaxID list: {value!r}"
        ) from exc

    if not taxids:
        raise ValueError(
            "At least one TaxID must be provided."
        )

    if any(taxid <= 0 for taxid in taxids):
        raise ValueError(
            "TaxIDs must be positive integers."
        )

    if len(taxids) != len(set(taxids)):
        raise ValueError(
            "Duplicate TaxIDs are not allowed."
        )

    return taxids


def parse_abundances(
    value: str,
) -> list[float]:
    """
    Parse comma-separated abundance fractions.

    Abundance is represented throughout VIMERA as a fraction:

        0.10   = 10%
        0.01   = 1%
        0.001  = 0.1%
    """

    try:
        abundances = [
            float(item)
            for item in parse_comma_separated(value)
        ]
    except ValueError as exc:
        raise ValueError(
            f"Invalid abundance list: {value!r}"
        ) from exc

    if not abundances:
        raise ValueError(
            "At least one abundance must be provided."
        )

    if any(
        abundance <= 0 or abundance > 1
        for abundance in abundances
    ):
        raise ValueError(
            "Abundances must be greater than 0 and at most 1."
        )

    return abundances

def _build_target_overrides(
    targets: str | None,
    target_fasta: list[str] | None,
    abundance: str | None,
) -> list[dict[str, Any]] | None:
    """Build target overrides in TaxID-then-FASTA order."""

    if targets is None and not target_fasta:
        return None

    target_overrides: list[dict[str, Any]] = []

    if targets is not None:
        target_overrides.extend(
            {"taxid": taxid}
            for taxid in parse_taxids(targets)
        )

    if target_fasta:
        target_overrides.extend(
            {"fasta_path": str(Path(path).expanduser())}
            for path in target_fasta
        )

    if not target_overrides:
        return None

    if abundance is None:
        return target_overrides

    abundances = parse_abundances(abundance)

    if len(abundances) == 1:
        for target in target_overrides:
            target["abundance"] = abundances[0]
    elif len(abundances) == len(target_overrides):
        for target, value in zip(
            target_overrides,
            abundances,
            strict=True,
        ):
            target["abundance"] = value
    else:
        raise ValueError(
            f"Received {len(abundances)} abundances for "
            f"{len(target_overrides)} targets. Supply one abundance "
            "to apply to every target, or one abundance per target."
        )
    return target_overrides


def build_cli_overrides(
    *,
    targets: str | None = None,
    target_fasta: list[str] | None = None,
    abundance: str | None = None,
    background_host: str | None = None,
    background_bacterial: str | None = None,
    background_viral: str | None = None,
    background_neighbor: str | None = None,
    background_abundance: float | None = None,
    platform: str | None = None,
    reads: int | None = None,
    replicates: int | None = None,
    seed: int | None = None,
    output_dir: str | None = None,
    experiment_name: str | None = None,
    reference_source: str | None = None,
    reference_cache: str | None = None,
    refresh_references: bool = False,
    max_genomes: int | None = None,
    batch_size: int | None = None,
) -> dict[str, Any]:
    """
    Convert CLI options into the internal configuration structure.

    Only explicitly supplied CLI values are returned.

    Precedence is enforced later by ``load_simulation_config``:

        CLI > YAML > defaults

    List-valued CLI options replace the corresponding YAML list.
    Nested dictionaries are merged recursively.
    """

    overrides: dict[str, Any] = {}

    # ---------------------------------------------------------------
    # Targets
    # ---------------------------------------------------------------

    target_overrides = _build_target_overrides(
        targets=targets,
        target_fasta=target_fasta,
        abundance=abundance,
    )

    if target_overrides is not None:
        overrides["targets"] = target_overrides

    elif abundance is not None:
        overrides["_cli_abundance"] = parse_abundances(
            abundance
        )
    # ---------------------------------------------------------------
    # Background
    # ---------------------------------------------------------------

    background: dict[str, Any] = {}

    if background_host is not None:
        background["host_taxids"] = parse_taxids(
            background_host
        )

    if background_bacterial is not None:
        background["bacterial_taxids"] = parse_taxids(
            background_bacterial
        )

    if background_viral is not None:
        background["viral_taxids"] = parse_taxids(
            background_viral
        )

    if background_neighbor is not None:
        background["near_neighbor_taxids"] = parse_taxids(
            background_neighbor
        )

    if background_abundance is not None:
        if background_abundance < 0 or background_abundance > 1:
            raise ValueError(
                "Background abundance must be between 0 and 1."
            )

        background["abundance"] = background_abundance

    if background:
        overrides["background"] = background
    # ---------------------------------------------------------------
    # Sequencing
    # ---------------------------------------------------------------

    sequencing: dict[str, Any] = {}

    if platform is not None:
        sequencing["platform"] = platform

    if reads is not None:
        sequencing["reads"] = reads

    if replicates is not None:
        sequencing["replicates"] = replicates

    if seed is not None:
        sequencing["seed"] = seed

    if sequencing:
        overrides["sequencing"] = sequencing

    # ---------------------------------------------------------------
    # Output
    # ---------------------------------------------------------------

    if output_dir is not None:
        overrides["output_dir"] = output_dir

    if experiment_name is not None:
        overrides["experiment_name"] = experiment_name

    # ---------------------------------------------------------------
    # Reference configuration
    # ---------------------------------------------------------------

    reference: dict[str, Any] = {}

    if reference_source is not None:
        reference["source"] = reference_source

    if reference_cache is not None:
        reference["cache_dir"] = reference_cache

    if refresh_references:
        reference["refresh"] = True
    if max_genomes is not None:
        reference["max_genomes"] = max_genomes

    if batch_size is not None:
        reference["batch_size"] = batch_size

    if reference:
        overrides["reference"] = reference

    return remove_none_values(overrides)


def _apply_yaml_target_abundance_override(
    merged: dict[str, Any],
    abundances: list[float],
) -> None:
    """
    Apply CLI abundances to targets already loaded from YAML.

    This allows:

        YAML:
            targets:
              - taxid: 11050
                abundance: 0.001

        CLI:
            --abundance 0.01

    to correctly produce an abundance of 0.01.

    The YAML target list itself is not replaced in this case.
    """

    targets = merged.get("targets")

    if not isinstance(targets, list) or not targets:
        raise ValueError(
            "--abundance requires targets to be defined "
            "either on the command line or in the YAML configuration."
        )

    if len(abundances) == 1:
        for target in targets:
            target["abundance"] = abundances[0]
        return

    if len(abundances) == len(targets):
        for target, abundance in zip(
            targets,
            abundances,
            strict=True,
        ):
            target["abundance"] = abundance
        return

    raise ValueError(
        "The number of abundances must be either 1 "
        "or equal to the number of configured targets."
    )


def load_simulation_config(
    config_path: Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> SimulationConfig:
    """
    Load and validate a simulation configuration.

    Precedence:

        CLI > YAML > defaults
    """

    # ---------------------------------------------------------------
    # 1. Defaults
    # ---------------------------------------------------------------

    defaults = deepcopy(
        DEFAULTS["simulation"]
    )

    # ---------------------------------------------------------------
    # 2. YAML
    # ---------------------------------------------------------------

    yaml_config: dict[str, Any] = {}

    if config_path is not None:
        yaml_config = load_yaml(config_path)

    merged = deep_merge(
        defaults,
        yaml_config,
    )

    # ---------------------------------------------------------------
    # 3. CLI
    # ---------------------------------------------------------------

    if cli_overrides:
        cli_overrides = deepcopy(
            cli_overrides
        )

        # Special handling for --abundance when --targets was
        # not simultaneously supplied.
        yaml_abundance = cli_overrides.pop(
            "_cli_abundance",
            None,
        )

        merged = deep_merge(
            merged,
            cli_overrides,
        )

        if yaml_abundance is not None:
            _apply_yaml_target_abundance_override(
                merged,
                yaml_abundance,
            )

    # ---------------------------------------------------------------
    # 4. Pydantic validation
    # ---------------------------------------------------------------

    config = SimulationConfig.model_validate(
        merged
    )

    return validate_simulation_config(
        config
    )


def save_resolved_config(
    config: SimulationConfig,
    path: Path,
) -> None:
    """Save the fully resolved configuration as YAML."""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = config.model_dump(
        mode="json"
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as handle:
        yaml.safe_dump(
            data,
            handle,
            sort_keys=False,
            default_flow_style=False,
        )