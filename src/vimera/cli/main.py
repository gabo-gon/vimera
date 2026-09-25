"""VIMERA command-line interface."""

from __future__ import annotations

import typer

from vimera.cli.simulate import simulate_command
from vimera.cli.null import null_command
from vimera.cli.spikein import spikein_command
from vimera.cli.confidence import confidence_command
from vimera.cli.evaluate import evaluate_command
from vimera.cli.report import report_command

app = typer.Typer(
    name="vimera",
    help=(
        "VIMERA: a reproducible framework for synthetic virome "
        "benchmarking and empirical viral detection assessment."
    ),
    no_args_is_help=True,
    add_completion=False,
)


@app.command("simulate")
def simulate(
    config: str | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to a YAML simulation configuration file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    targets: str | None = typer.Option(
        None,
        "--targets",
        "-t",
        help="Comma-separated target TaxIDs. Replaces targets from YAML.",
    ),
    abundance: str | None = typer.Option(
        None,
        "--abundance",
        "-a",
        help=(
            "Comma-separated target abundances as fractions. "
            "One value applies to all targets; otherwise one value per target."
        ),
    ),
    background_host: str | None = typer.Option(
        None,
        "--background-host",
        help="Comma-separated host background TaxIDs.",
    ),
    background_bacterial: str | None = typer.Option(
        None,
        "--background-bacterial",
        help="Comma-separated bacterial background TaxIDs.",
    ),
    background_viral: str | None = typer.Option(
        None,
        "--background-viral",
        help="Comma-separated viral background TaxIDs.",
    ),
    background_neighbor: str | None = typer.Option(
        None,
        "--background-neighbor",
        help="Comma-separated near-neighbor viral TaxIDs.",
    ),
    background_abundance: float | None = typer.Option(
        None,
        "--background-abundance",
        min=0.0,
        max=1.0,
        help="Total background abundance as a fraction of the sample.",
    ),
    platform: str | None = typer.Option(
        None,
        "--platform",
        help="Sequencing platform: illumina or ont.",
    ),
    reads: int | None = typer.Option(
        None,
        "--reads",
        "-n",
        min=1,
        help="Number of reads to simulate per replicate.",
    ),
    replicates: int | None = typer.Option(
        None,
        "--replicates",
        "-r",
        min=1,
        help="Number of independent simulation replicates.",
    ),
    seed: int | None = typer.Option(
        None,
        "--seed",
        help="Random seed for reproducible simulation.",
    ),
    output_dir: str | None = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Output directory. Replaces the YAML value.",
    ),
    experiment_name: str | None = typer.Option(
        None,
        "--experiment-name",
        help="Experiment name. Replaces the YAML value.",
    ),
    reference_source: str | None = typer.Option(
        None,
        "--reference-source",
        help=(
            "Reference source: auto, local, or ncbi."
        ),
    ),
    reference_cache: str | None = typer.Option(
        None,
        "--reference-cache",
        help=(
            "Global VIMERA reference cache directory. "
            "Defaults to ~/.vimera/references."
        ),
    ),
     refresh_references: bool = typer.Option(
        False,
        "--refresh-references",
        help=(
            "Refresh cached references by querying NCBI again."
        ),
    ),
    max_genomes: int = typer.Option(
        10,
        "--max-genomes",
        min=1,
        help=(
            "Maximum number of reference genomes to retrieve "
            "per target."
        ),
    ),
    batch_size: int = typer.Option(
        100,
        "--batch-size",
        min=1,
        help=(
            "Maximum number of genomes requested from NCBI "
            "per batch."
        ),
    ),
    ) -> None:
    """Generate a controlled synthetic virome dataset."""

    simulate_command(
        config_path=config,
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

@app.command("version")
def version() -> None:
    """Show the installed VIMERA version."""
    from vimera import __version__

    typer.echo(f"VIMERA {__version__}")

@app.command("null")
def null(
    config: str | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to a YAML null configuration file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    input_fastq: str | None = typer.Option(
        None,
        "--input-fastq",
        help="Original FASTQ file containing the reads.",
    ),
    read_group: str | None = typer.Option(
        None,
        "--read-group",
        help="TSV file defining the reads belonging to the observed group.",
    ),
    replicates: int | None = typer.Option(
        None,
        "--replicates",
        "-r",
        min=1,
        help="Number of null replicates to generate.",
    ),
    seed: int | None = typer.Option(
        None,
        "--seed",
        help="Random seed.",
    ),
    output_dir: str | None = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Output directory.",
    ),
) -> None:
    """Generate an empirical target-absent null distribution."""
    null_command(
        config_path=config,
        input_fastq=input_fastq,
        read_group=read_group,
        replicates=replicates,
        seed=seed,
        output_dir=output_dir,
    )

@app.command("spikein")
def spikein(
    config: str | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to a YAML spike-in configuration file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    input_fastq: str | None = typer.Option(
        None,
        "--input-fastq",
        help="Original FASTQ used as the real-sample background.",
    ),
    target_taxids: str | None = typer.Option(
        None,
        "--target-taxids",
        "-t",
        help="Comma-separated target TaxIDs. Replaces YAML targets.",
    ),
    abundances: str | None = typer.Option(
        None,
        "--abundances",
        "-a",
        help=(
            "Comma-separated target abundances. One value applies to "
            "all targets; otherwise one value per target."
        ),
    ),
    replicates: int | None = typer.Option(
        None,
        "--replicates",
        "-r",
        min=1,
        help="Number of independent spike-in replicates.",
    ),
    seed: int | None = typer.Option(
        None,
        "--seed",
        help="Random seed.",
    ),
    output_dir: str | None = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Output directory.",
    ),
) -> None:
    """Create controlled target-present spike-in datasets."""
    spikein_command(
        config_path=config,
        input_fastq=input_fastq,
        target_taxids=target_taxids,
        abundances=abundances,
        replicates=replicates,
        seed=seed,
        output_dir=output_dir,
    )

@app.command("confidence")
def confidence(
    observed: float = typer.Option(
        ...,
        "--observed",
        help="Observed detection statistic.",
    ),
    null_file: str = typer.Option(
        ...,
        "--null",
        help="Null-distribution file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    spikein_file: str | None = typer.Option(
        None,
        "--spikein",
        help="Optional spike-in detection results.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Optional output TSV.",
    ),
) -> None:
    """Assess empirical confidence of an observed viral detection."""
    confidence_command(
        observed=observed,
        null_file=null_file,
        spikein_file=spikein_file,
        output=output,
    )
@app.command("evaluate")
def evaluate(
    predictions: str = typer.Option(
        ...,
        "--predictions",
        "-p",
        help="Prediction/results table produced by the pipeline.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    truth: str = typer.Option(
        ...,
        "--truth",
        "-t",
        help="VIMERA ground-truth table.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Optional output TSV.",
    ),
    group_by: str | None = typer.Option(
        None,
        "--group-by",
        help="Optional column for stratified evaluation.",
    ),
) -> None:
    """Evaluate pipeline results against known ground truth."""
    evaluate_command(
        predictions=predictions,
        truth=truth,
        output=output,
        group_by=group_by,
    )

@app.command("report")
def report(
    input_dir: str = typer.Option(
        ...,
        "--input",
        "-i",
        help="Directory containing VIMERA result files.",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    output: str = typer.Option(
        ...,
        "--output",
        "-o",
        help="Output report path.",
    ),
    report_type: str = typer.Option(
        "auto",
        "--type",
        "-t",
        help=(
            "Report type: auto, synthetic, null, spikein, "
            "evaluation, or complete."
        ),
    ),
    format: str = typer.Option(
        "html",
        "--format",
        "-f",
        help="Report format: html or pdf.",
    ),
) -> None:
    """Generate a report from VIMERA analysis results."""
    report_command(
        input_dir=input_dir,
        output=output,
        report_type=report_type,
        format=format,
    )
    
if __name__ == "__main__":
    app()