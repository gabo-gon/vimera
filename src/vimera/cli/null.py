"""CLI entry point for empirical null-distribution generation."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from vimera.config.loader import load_yaml
from vimera.config.models import NullConfig
from vimera.config.defaults import DEFAULT_NULL_CONFIG

console = Console()


def null_command(
    *,
    config_path: str | None,
    input_fastq: str | None,
    read_group: str | None,
    replicates: int | None,
    seed: int | None,
    output_dir: str | None,
) -> None:
    """Generate an empirical target-absent null distribution.

    Configuration precedence:

        CLI > YAML > defaults

    CLI values replace the corresponding YAML values.
    """

    try:
        config = _load_null_config(
            config_path=config_path,
            input_fastq=input_fastq,
            read_group=read_group,
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
    # Null-generation engine
    # ------------------------------------------------------------------
    #
    # The scientific implementation belongs in:
    #
    #     vimera.empirical.nulls
    #
    # For example:
    #
    # from vimera.empirical.nulls import generate_null_distribution
    #
    # generate_null_distribution(
    #     config=config,
    # )
    #
    # The CLI should not contain sampling or FASTQ-processing logic.
    # ------------------------------------------------------------------

    console.print(
        "\n[yellow]Null-generation engine not yet implemented.[/yellow]"
    )
    console.print(
        "Configuration was successfully resolved."
    )


def _load_null_config(
    *,
    config_path: str | None,
    input_fastq: str | None,
    read_group: str | None,
    replicates: int | None,
    seed: int | None,
    output_dir: str | None,
) -> NullConfig:
    """Load and resolve the null configuration."""

    config_data = dict(DEFAULT_NULL_CONFIG)

    # --------------------------------------------------------------
    # YAML configuration
    # --------------------------------------------------------------
    if config_path is not None:
        yaml_data = load_yaml(Path(config_path))

        if not isinstance(yaml_data, dict):
            raise ValueError(
                "Null configuration must contain a YAML mapping."
            )

        # YAML values replace defaults.
        config_data.update(yaml_data)

    # --------------------------------------------------------------
    # CLI overrides
    # --------------------------------------------------------------
    #
    # CLI values replace YAML values rather than merging with them.
    #
    cli_values = {
        "input_fastq": input_fastq,
        "read_group": read_group,
        "replicates": replicates,
        "seed": seed,
        "output_dir": output_dir,
    }

    for key, value in cli_values.items():
        if value is not None:
            config_data[key] = value

    # --------------------------------------------------------------
    # Required fields
    # --------------------------------------------------------------
    if not config_data.get("input_fastq"):
        raise ValueError(
            "Missing input FASTQ. Provide 'input_fastq' in YAML "
            "or use --input-fastq."
        )

    if not config_data.get("read_group"):
        raise ValueError(
            "Missing read-group file. Provide 'read_group' in YAML "
            "or use --read-group."
        )

    config = NullConfig.model_validate(config_data)

    # --------------------------------------------------------------
    # Input validation
    # --------------------------------------------------------------
    input_path = Path(config.input_fastq)
    group_path = Path(config.read_group)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input FASTQ does not exist: {input_path}"
        )

    if not group_path.exists():
        raise FileNotFoundError(
            f"Read-group file does not exist: {group_path}"
        )

    return config


def _print_configuration(config: NullConfig) -> None:
    """Print a concise summary of the resolved null configuration."""

    console.print()

    console.print(
        Panel(
            "[bold]VIMERA empirical null distribution[/bold]",
            border_style="green",
        )
    )

    console.print(
        f"[bold]Input FASTQ:[/bold] {config.input_fastq}"
    )
    console.print(
        f"[bold]Read groups:[/bold] {config.read_group}"
    )
    console.print(
        f"[bold]Replicates:[/bold] {config.replicates:,}"
    )

    if config.seed is None:
        console.print(
            "[bold]Seed:[/bold] random"
        )
    else:
        console.print(
            f"[bold]Seed:[/bold] {config.seed}"
        )

    console.print(
        f"[bold]Output:[/bold] {config.output_dir}"
    )

