"""CLI entry point for empirical viral detection confidence assessment."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from vimera.empirical.confidence import (
    calculate_empirical_confidence,
)

console = Console()


def confidence_command(
    *,
    observed: float,
    null_file: str,
    spikein_file: str | None = None,
    output: str | None = None,
) -> None:
    """Assess an observed viral detection signal against empirical nulls.

    The observed statistic is compared with a target-absent null
    distribution. If spike-in results are supplied, they can additionally
    be used to characterize detection performance in the sample background.

    This produces empirical/simulation-based confidence metrics and should
    not be interpreted as conventional biological significance.
    """

    try:
        null_path = Path(null_file)

        if not null_path.exists():
            raise FileNotFoundError(
                f"Null distribution does not exist: {null_path}"
            )

        spikein_path: Path | None = None

        if spikein_file is not None:
            spikein_path = Path(spikein_file)

            if not spikein_path.exists():
                raise FileNotFoundError(
                    f"Spike-in results do not exist: {spikein_path}"
                )

        result = calculate_empirical_confidence(
            observed_statistic=observed,
            null_file=null_path,
            spikein_file=spikein_path,
        )

    except FileNotFoundError as exc:
        raise typer.BadParameter(str(exc)) from exc

    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    except Exception as exc:
        console.print(
            Panel(
                f"[red]Confidence assessment failed:[/red]\n{exc}",
                title="VIMERA",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from exc

    _print_result(result)

    if output is not None:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        _write_result(result, output_path)

        console.print(
            f"\n[bold]Result:[/bold] {output_path}"
        )


def _print_result(result) -> None:
    """Print confidence results."""

    console.print()

    console.print(
        Panel(
            "[bold]VIMERA empirical confidence assessment[/bold]",
            border_style="green",
        )
    )

    console.print(
        f"[bold]Observed statistic:[/bold] "
        f"{result.observed_statistic:g}"
    )

    console.print(
        f"[bold]Null replicates:[/bold] "
        f"{result.n_null:,}"
    )

    console.print(
        f"[bold]Null mean:[/bold] "
        f"{result.null_mean:g}"
    )

    console.print(
        f"[bold]Null SD:[/bold] "
        f"{result.null_sd:g}"
    )

    console.print(
        f"[bold]Null percentile:[/bold] "
        f"{result.null_percentile:.2f}%"
    )

    console.print(
        f"[bold]Empirical p-value:[/bold] "
        f"{result.empirical_p:.6g}"
    )

    console.print(
        f"[bold]Effect size:[/bold] "
        f"{result.effect_size:g}"
    )

    if result.detection_assessment is not None:
        console.print(
            f"[bold]Spike-in detection assessment:[/bold] "
            f"{result.detection_assessment}"
        )


def _write_result(result, output_path: Path) -> None:
    """Write confidence results as a TSV file."""

    fields = [
        "observed_statistic",
        "n_null",
        "null_mean",
        "null_sd",
        "null_percentile",
        "empirical_p",
        "effect_size",
        "detection_assessment",
    ]

    with output_path.open("w", encoding="utf-8") as handle:
        handle.write("\t".join(fields) + "\n")

        values = [
            result.observed_statistic,
            result.n_null,
            result.null_mean,
            result.null_sd,
            result.null_percentile,
            result.empirical_p,
            result.effect_size,
            result.detection_assessment,
        ]

        handle.write(
            "\t".join(
                "" if value is None else str(value)
                for value in values
            )
            + "\n"
        )