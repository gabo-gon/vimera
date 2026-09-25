"""CLI entry point for synthetic virome simulation."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from vimera.config.loader import (
    build_cli_overrides,
    load_simulation_config,
    save_resolved_config,
)
from vimera.config.validation import validate_simulation_config
from vimera.synthetic.benchmark import run_benchmark

console = Console()


def simulate_command(
    *,
    config_path: str | None,
    targets: str | None,
    abundance: str | None,
    background_host: str | None,
    background_bacterial: str | None,
    background_viral: str | None,
    background_neighbor: str | None,
    background_abundance: float | None,
    platform: str | None,
    reads: int | None,
    replicates: int | None,
    seed: int | None,
    output_dir: str | None,
    experiment_name: str | None,
    reference_source: str | None,
    reference_cache: str | None,
    refresh_references: bool,
    max_genomes: int,
    batch_size: int,
) -> None:
    """Resolve configuration and execute a synthetic simulation.

    The CLI follows the precedence:

        CLI > YAML > defaults

    CLI values replace the corresponding YAML values. In particular,
    list-valued CLI options replace the complete YAML list rather than
    being appended to it.
    """

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    try:
        cli_overrides = build_cli_overrides(
            targets=targets,
            abundance=abundance,
            background_host=background_host,
            background_bacterial=background_bacterial,
            background_viral=background_viral,
            background_neighbor=background_neighbor,
            background_abundance=background_abundance,
            platform=platform,
            reads=reads,
            replicates=replicates,
            seed=seed,
            output_dir=output_dir,
            experiment_name=experiment_name,
            reference_source=reference_source,
            reference_cache=reference_cache,
            refresh_references=refresh_references,
            max_genomes=max_genomes,
            batch_size=batch_size,
        )

        config = load_simulation_config(
            config_path=Path(config_path) if config_path else None,
            cli_overrides=cli_overrides,
        )

        validate_simulation_config(config)

    except FileNotFoundError as exc:
        raise typer.BadParameter(str(exc)) from exc

    except ValueError as exc:
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

    # ------------------------------------------------------------------
    # Output directory and resolved configuration
    # ------------------------------------------------------------------

    output_dir_path = Path(config.output_dir)
    experiment_dir = (
        output_dir_path
        / config.experiment_name
    )

    experiment_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    resolved_config_path = (
        experiment_dir
        / "config.yml"
    )

    save_resolved_config(
        config,
        resolved_config_path,
    )

    _print_resolved_configuration(
        config=config,
        resolved_config_path=resolved_config_path,
    )

    # ------------------------------------------------------------------
    # Run simulation
    # ------------------------------------------------------------------

    console.print(
        "\n[bold]Resolving reference genomes...[/bold]"
    )

    try:
        datasets = run_benchmark(config)

    except Exception as exc:
        console.print(
            Panel(
                f"[red]Simulation failed:[/red]\n{exc}",
                title="VIMERA",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from exc

    console.print(
        "\n[green]Simulation completed.[/green]"
    )

    # ------------------------------------------------------------------
    # Report resolved references
    # ------------------------------------------------------------------

    if datasets:
        console.print(
            f"\n[bold]Generated dataset(s):[/bold] "
            f"{len(datasets)}"
        )

        for dataset in datasets:
            console.print(
                f"\n  Replicate {dataset.replicate}"
            )

            if dataset.fastq_r1:
                console.print(
                    f"    R1: {dataset.fastq_r1}"
                )

            if dataset.fastq_r2:
                console.print(
                    f"    R2: {dataset.fastq_r2}"
                )

            if dataset.truth_path:
                console.print(
                    f"    Truth: {dataset.truth_path}"
                )

            if dataset.abundance_path:
                console.print(
                    f"    Abundance: {dataset.abundance_path}"
                )

    console.print(
        f"\n[bold]Reference source:[/bold] "
        f"{config.reference.source.value}"
    )

    console.print(
        f"[bold]Reference cache:[/bold] "
        f"{config.reference.cache_dir}"
    )

    console.print(
        f"[bold]Refresh references:[/bold] "
        f"{config.reference.refresh}"
    )


def _print_resolved_configuration(
    *,
    config,
    resolved_config_path: Path,
) -> None:
    """Display a concise summary of the resolved simulation."""

    console.print()

    console.print(
        Panel(
            "[bold]VIMERA synthetic simulation[/bold]",
            border_style="green",
        )
    )

    console.print(
        f"[bold]Experiment:[/bold] "
        f"{config.experiment_name}"
    )

    console.print(
        f"[bold]Platform:[/bold] "
        f"{config.sequencing.platform.value}"
    )

    console.print(
        f"[bold]Reads:[/bold] "
        f"{config.sequencing.reads:,}"
    )

    console.print(
        f"[bold]Replicates:[/bold] "
        f"{config.sequencing.replicates}"
    )

    console.print(
        "\n[bold]Targets:[/bold]"
    )

    for target in config.targets:
        console.print(
            f"  • TaxID {target.taxid}"
            f" — abundance={target.abundance:g}"
            f" — genome_selection="
            f"{target.genome_selection.value}"
        )

    console.print(
        f"\n[bold]Resolved configuration:[/bold] "
        f"{resolved_config_path}"
    )