
"""CLI command for sequence evolution."""

from pathlib import Path

import typer

from vimera.synthetic.evolution import simulate_evolution


def simulate_evolution_command(
    input_fasta: Path = typer.Option(
        ...,
        "--input-fasta",
        exists=True,
        readable=True,
        dir_okay=False,
        help="Input FASTA containing DNA sequences.",
    ),
    distance: float = typer.Option(
        ...,
        "--distance",
        min=0.0,
        max=1.0,
        help="Target nucleotide divergence, from 0 to 1.",
    ),
    output_fasta: Path = typer.Option(
        Path("evolved.fasta"),
        "--output-fasta",
        dir_okay=False,
        help="Output FASTA path.",
    ),
    replicates: int = typer.Option(
        1,
        "--replicates",
        min=1,
        help="Number of descendants per input sequence.",
    ),
    seed: int | None = typer.Option(
        None,
        "--seed",
        help="Random seed for reproducibility.",
    ),
    kappa: float = typer.Option(
        2.0,
        "--kappa",
        min=0.000001,
        help="Transition/transversion substitution weight ratio.",
    ),
) -> None:
    """Generate evolved DNA sequences at a specified divergence."""
    try:
        result = simulate_evolution(
            input_fasta=input_fasta,
            output_fasta=output_fasta,
            distance=distance,
            replicates=replicates,
            seed=seed,
            kappa=kappa,
        )
    except (ValueError, OSError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(f"Evolved FASTA: {result}")
    typer.echo(
        f"Evolution metrics: {result.with_suffix('.evolution.tsv')}"
    )
