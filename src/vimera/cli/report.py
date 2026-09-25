"""CLI entry point for VIMERA report generation."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

console = Console()


def report_command(
    *,
    input_dir: str,
    output: str,
    report_type: str = "auto",
    format: str = "html",
) -> None:
    """Generate a report from VIMERA analysis results.

    Parameters
    ----------
    input_dir:
        Directory containing VIMERA result files.

    output:
        Output report path.

    report_type:
        Type of report to generate. Supported values are ``auto``,
        ``synthetic``, ``null``, ``spikein``, ``evaluation``, and
        ``complete``.

    format:
        Report format. Currently ``html`` is the initial target format.
    """

    try:
        input_path = Path(input_dir)

        if not input_path.exists():
            raise FileNotFoundError(
                f"Input results directory does not exist: {input_path}"
            )

        if not input_path.is_dir():
            raise ValueError(
                f"Input path is not a directory: {input_path}"
            )

        report_type = report_type.lower()
        format = format.lower()

        valid_report_types = {
            "auto",
            "synthetic",
            "null",
            "spikein",
            "evaluation",
            "complete",
        }

        if report_type not in valid_report_types:
            raise ValueError(
                f"Unsupported report type: {report_type}. "
                f"Choose from: {', '.join(sorted(valid_report_types))}."
            )

        valid_formats = {"html", "pdf"}

        if format not in valid_formats:
            raise ValueError(
                f"Unsupported report format: {format}. "
                f"Choose from: {', '.join(sorted(valid_formats))}."
            )

        # --------------------------------------------------------------
        # Report engine
        # --------------------------------------------------------------
        #
        # The actual report-generation logic belongs in:
        #
        #     vimera.reporting.tables
        #     vimera.reporting.plots
        #     vimera.reporting.reports
        #
        # For example:
        #
        # from vimera.reporting.reports import generate_report
        #
        # generate_report(
        #     input_dir=input_path,
        #     output=output_path,
        #     report_type=report_type,
        #     format=format,
        # )
        #
        # --------------------------------------------------------------

        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        result = _placeholder_report(
            input_dir=input_path,
            output=output_path,
            report_type=report_type,
            format=format,
        )

    except FileNotFoundError as exc:
        raise typer.BadParameter(str(exc)) from exc

    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc

    except Exception as exc:
        console.print(
            Panel(
                f"[red]Report generation failed:[/red]\n{exc}",
                title="VIMERA",
                border_style="red",
            )
        )
        raise typer.Exit(code=1) from exc

    _print_result(result)


def _placeholder_report(
    *,
    input_dir: Path,
    output: Path,
    report_type: str,
    format: str,
) -> dict:
    """Temporary placeholder until the reporting engine is implemented."""

    return {
        "input_dir": str(input_dir),
        "output": str(output),
        "report_type": report_type,
        "format": format,
        "status": "not_implemented",
    }


def _print_result(result: dict) -> None:
    """Print a concise report-generation summary."""

    console.print()

    console.print(
        Panel(
            "[bold]VIMERA report generation[/bold]",
            border_style="green",
        )
    )

    console.print(
        f"[bold]Input:[/bold] {result['input_dir']}"
    )

    console.print(
        f"[bold]Report type:[/bold] {result['report_type']}"
    )

    console.print(
        f"[bold]Format:[/bold] {result['format']}"
    )

    console.print(
        f"[bold]Output:[/bold] {result['output']}"
    )

    if result.get("status") == "not_implemented":
        console.print(
            "\n[yellow]Reporting engine not yet implemented.[/yellow]"
        )
        console.print(
            "The input directory and report parameters were validated."
        )
    else:
        console.print(
            "\n[green]Report generated successfully.[/green]"
        )