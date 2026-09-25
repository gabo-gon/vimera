"""CLI entry point for VIMERA benchmark evaluation."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

console = Console()


def evaluate_command(
    *,
    predictions: str,
    truth: str,
    output: str | None = None,
    group_by: str | None = None,
) -> None:
    """Evaluate detection or classification results against ground truth.

    Parameters
    ----------
    predictions:
        File containing results produced by the pipeline being evaluated.

    truth:
        VIMERA truth table describing the known origin/status of reads.

    output:
        Optional path for the resulting metrics table.

    group_by:
        Optional column by which to stratify evaluation results.

    Notes
    -----
    VIMERA does not require a particular classifier. The prediction table
    can originate from Kraken2, Kaiju, BLAST, read mapping, an assembler,
    or a custom analysis pipeline, provided it is converted to the
    standardized prediction format.
    """

    try:
        predictions_path = Path(predictions)
        truth_path = Path(truth)

        if not predictions_path.exists():
            raise FileNotFoundError(
                f"Prediction file does not exist: {predictions_path}"
            )

        if not truth_path.exists():
            raise FileNotFoundError(
                f"Truth file does not exist: {truth_path}"
            )

        # --------------------------------------------------------------
        # Evaluation engine
        # --------------------------------------------------------------
        #
        # The scientific implementation belongs in:
        #
        #     vimera.evaluation.classification
        #     vimera.evaluation.detection
        #     vimera.evaluation.metrics
        #
        # For example:
        #
        # from vimera.evaluation.classification import evaluate_predictions
        #
        # result = evaluate_predictions(
        #     predictions=predictions_path,
        #     truth=truth_path,
        #     group_by=group_by,
        # )
        #
        # --------------------------------------------------------------

        result = _placeholder_evaluation(
            predictions_path=predictions_path,
            truth_path=truth_path,
            group_by=group_by,
        )

    except FileNotFoundError as exc:
        raise typer.BadParameter(str(exc)) from exc

    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    except Exception as exc:
        console.print(
            Panel(
                f"[red]Evaluation failed:[/red]\n{exc}",
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
            f"\n[bold]Results:[/bold] {output_path}"
        )


def _placeholder_evaluation(
    *,
    predictions_path: Path,
    truth_path: Path,
    group_by: str | None,
) -> dict:
    """Temporary placeholder until the evaluation engine is implemented."""

    return {
        "predictions": str(predictions_path),
        "truth": str(truth_path),
        "group_by": group_by,
        "status": "not_implemented",
    }


def _print_result(result: dict) -> None:
    """Print a concise evaluation summary."""

    console.print()

    console.print(
        Panel(
            "[bold]VIMERA benchmark evaluation[/bold]",
            border_style="green",
        )
    )

    if result.get("status") == "not_implemented":
        console.print(
            "[yellow]Evaluation engine not yet implemented.[/yellow]"
        )

        console.print(
            f"[bold]Predictions:[/bold] {result['predictions']}"
        )

        console.print(
            f"[bold]Truth:[/bold] {result['truth']}"
        )

        if result.get("group_by") is not None:
            console.print(
                f"[bold]Group by:[/bold] {result['group_by']}"
            )

        console.print(
            "\nThe input files were successfully located."
        )

        return

    for key, value in result.items():
        console.print(
            f"[bold]{key}:[/bold] {value}"
        )


def _write_result(
    result: dict,
    output_path: Path,
) -> None:
    """Write evaluation results as a TSV file."""

    with output_path.open("w", encoding="utf-8") as handle:
        handle.write("metric\tvalue\n")

        for key, value in result.items():
            handle.write(
                f"{key}\t{value}\n"
            )