"""CLI entry point for empirical spike-in experiments."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from vimera.config.defaults import DEFAULT_SPIKEIN_CONFIG
from vimera.config.loader import load_yaml
from vimera.config.models import SpikeInConfig

console = Console()


def spikein_command(
    *,
    config_path: str | None,
    input_fastq: str | None,
    target_taxids: str | None,
    abundances: str | None,
    replicates: int | None,
    seed: int | None,
    output_dir: str | None,
) -> None:
    """Run a controlled viral spike-in experiment.

    Configuration precedence:

        CLI > YAML > defaults

    CLI values replace the corresponding YAML values. In particular,
    list-valued CLI options replace the complete YAML list.
    """

    try:
        config = _load_spikein_config(
            config_path=config_path,
            input_fastq=input_fastq,
            target_taxids=target_taxids,
            abundances=abundances,
            replicates=replicates,
            seed=seed,
            output_dir=output_dir,
        )

    except (ValueError, FileNotFoundError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    except Exception as exc:
        console.print(
            Panel(
                f"[red]Configuration error:[/red]\n{exc}",
                title="VIMERA",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from exc

    output_path = Path(config.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    _print_configuration(config)

    # ------------------------------------------------------------------
    # Spike-in engine
    # ------------------------------------------------------------------
    #
    # The actual scientific implementation belongs in:
    #
    #     vimera.empirical.spikeins
    #
    # For example:
    #
    # from vimera.empirical.spikeins import run_spikein_experiment
    #
    # run_spikein_experiment(
    #     config=config,
    # )
    #
    # The CLI deliberately does not perform FASTQ manipulation or
    # sequencing simulation itself.
    # ------------------------------------------------------------------

    console.print(
        "\n[yellow]Spike-in engine not yet implemented.[/yellow]"
    )
    console.print(
        "Configuration was successfully resolved."
    )


def _load_spikein_config(
    *,
    config_path: str | None,
    input_fastq: str | None,
    target_taxids: str | None,
    abundances: str | None,
    replicates: int | None,
    seed: int | None,
    output_dir: str | None,
) -> SpikeInConfig:
    """Load and resolve the spike-in configuration."""

    config_data = dict(DEFAULT_SPIKEIN_CONFIG)

    # --------------------------------------------------------------
    # YAML
    # --------------------------------------------------------------
    if config_path is not None:
        yaml_data = load_yaml(Path(config_path))

        if not isinstance(yaml_data, dict):
            raise ValueError(
                "Spike-in configuration must contain a YAML mapping."
            )

        config_data.update(yaml_data)

    # --------------------------------------------------------------
    # CLI
    # --------------------------------------------------------------
    #
    # CLI values replace YAML values.
    #
    cli_values = {
        "input_fastq": input_fastq,
        "replicates": replicates,
        "seed": seed,
        "output_dir": output_dir,
    }

    for key, value in cli_values.items():
        if value is not None:
            config_data[key] = value

    # --------------------------------------------------------------
    # Target TaxIDs
    # --------------------------------------------------------------
    if target_taxids is not None:
        taxid_values = _parse_taxids(target_taxids)

        if not taxid_values:
            raise ValueError(
                "--target-taxids must contain at least one TaxID."
            )

        config_data["target_taxids"] = taxid_values

    # --------------------------------------------------------------
    # Abundances
    # --------------------------------------------------------------
    if abundances is not None:
        abundance_values = _parse_abundances(abundances)

        if not abundance_values:
            raise ValueError(
                "--abundances must contain at least one abundance."
            )

        config_data["abundances"] = abundance_values

    # --------------------------------------------------------------
    # Required fields
    # --------------------------------------------------------------
    if not config_data.get("input_fastq"):
        raise ValueError(
            "Missing input FASTQ. Provide 'input_fastq' in YAML "
            "or use --input-fastq."
        )

    if not config_data.get("target_taxids"):
        raise ValueError(
            "Missing target TaxIDs. Provide 'target_taxids' in YAML "
            "or use --target-taxids."
        )

    if not config_data.get("abundances"):
        raise ValueError(
            "Missing target abundances. Provide 'abundances' in YAML "
            "or use --abundances."
        )

    config = SpikeInConfig.model_validate(config_data)

    # --------------------------------------------------------------
    # Input validation
    # --------------------------------------------------------------
    input_path = Path(config.input_fastq)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input FASTQ does not exist: {input_path}"
        )

    # --------------------------------------------------------------
    # Target/abundance consistency
    # --------------------------------------------------------------
    if len(config.abundances) not in (1, len(config.target_taxids)):
        raise ValueError(
            "The number of abundances must be either 1 or equal to "
            "the number of target TaxIDs."
        )

    return config


def _parse_taxids(value: str) -> list[int]:
    """Parse comma-separated TaxIDs."""

    try:
        taxids = [int(item.strip()) for item in value.split(",")]
    except ValueError as exc:
        raise ValueError(
            f"Invalid TaxID list: {value!r}"
        ) from exc

    if any(taxid <= 0 for taxid in taxids):
        raise ValueError(
            "TaxIDs must be positive integers."
        )

    return taxids


def _parse_abundances(value: str) -> list[float]:
    """Parse comma-separated abundances."""

    try:
        abundances = [
            float(item.strip())
            for item in value.split(",")
        ]
    except ValueError as exc:
        raise ValueError(
            f"Invalid abundance list: {value!r}"
        ) from exc

    if any(abundance <= 0 or abundance > 1 for abundance in abundances):
        raise ValueError(
            "Abundances must be greater than 0 and no greater than 1."
        )

    return abundances


def _print_configuration(config: SpikeInConfig) -> None:
    """Print a concise summary of the resolved configuration."""

    console.print()

    console.print(
        Panel(
            "[bold]VIMERA empirical spike-in experiment[/bold]",
            border_style="green",
        )
    )

    console.print(
        f"[bold]Input FASTQ:[/bold] {config.input_fastq}"
    )

    console.print(
        f"[bold]Replicates:[/bold] {config.replicates:,}"
    )

    if config.seed is None:
        console.print("[bold]Seed:[/bold] random")
    else:
        console.print(
            f"[bold]Seed:[/bold] {config.seed}"
        )

    console.print(
        f"[bold]Output:[/bold] {config.output_dir}"
    )

    console.print("\n[bold]Targets:[/bold]")

    abundances = _expand_abundances(
        config.abundances,
        len(config.target_taxids),
    )

    for taxid, abundance in zip(
        config.target_taxids,
        abundances,
        strict=True,
    ):
        console.print(
            f"  • TaxID {taxid} — abundance={abundance:g}"
        )


def _expand_abundances(
    abundances: list[float],
    n_targets: int,
) -> list[float]:
    """Expand a single abundance to all targets."""

    if len(abundances) == 1:
        return abundances * n_targets

    return abundances