
"""Generate evolved DNA sequences at a specified observed divergence."""

from __future__ import annotations

import csv
import random
from collections import Counter
from pathlib import Path
from typing import Iterator

BASES = "ACGT"
TRANSITIONS = {
    ("A", "G"), ("G", "A"),
    ("C", "T"), ("T", "C"),
}


def read_fasta(path: Path) -> Iterator[tuple[str, str]]:
    """Yield (record_id, sequence) pairs from a FASTA file."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"FASTA file not found: {path}")

    record_id: str | None = None
    chunks: list[str] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue

            if line.startswith(">"):
                if record_id is not None:
                    sequence = "".join(chunks).upper()
                    if not sequence:
                        raise ValueError(
                            f"Empty FASTA record: {record_id}"
                        )
                    yield record_id, sequence

                header = line[1:].strip()
                if not header:
                    raise ValueError(
                        f"Empty FASTA identifier at line {line_number}"
                    )

                record_id = header.split()[0]
                chunks = []
            else:
                if record_id is None:
                    raise ValueError(
                        f"Sequence data before FASTA header "
                        f"at line {line_number}"
                    )
                chunks.append("".join(line.split()))

    if record_id is not None:
        sequence = "".join(chunks).upper()
        if not sequence:
            raise ValueError(f"Empty FASTA record: {record_id}")
        yield record_id, sequence


def estimate_substitution_matrix(
    sequence: str,
    *,
    kappa: float = 2.0,
    pseudocount: float = 0.5,
) -> dict[str, dict[str, float]]:
    """Create composition-weighted substitution probabilities.

    Destination-base frequencies are estimated from the input sequence.
    Transitions are weighted by kappa relative to transversions.

    This is a simple model-based substitution matrix, not an empirical
    estimate of evolutionary substitution rates.
    """
    if kappa <= 0:
        raise ValueError("kappa must be greater than zero.")
    if pseudocount <= 0:
        raise ValueError("pseudocount must be greater than zero.")

    counts = Counter(
        base for base in sequence.upper() if base in BASES
    )
    total = sum(counts.values())

    if total == 0:
        raise ValueError(
            "Sequence contains no unambiguous DNA bases (A, C, G, T)."
        )

    frequencies = {
        base: (counts[base] + pseudocount)
        / (total + pseudocount * len(BASES))
        for base in BASES
    }

    matrix: dict[str, dict[str, float]] = {}

    for source in BASES:
        weights: dict[str, float] = {}

        for destination in BASES:
            if destination == source:
                continue

            weight = frequencies[destination]
            if (source, destination) in TRANSITIONS:
                weight *= kappa

            weights[destination] = weight

        denominator = sum(weights.values())
        matrix[source] = {
            base: weight / denominator
            for base, weight in weights.items()
        }

    return matrix


def _sample_base(
    probabilities: dict[str, float],
    rng: random.Random,
) -> str:
    """Sample a destination nucleotide from its probability weights."""
    draw = rng.random()
    cumulative = 0.0

    for base, probability in probabilities.items():
        cumulative += probability
        if draw < cumulative:
            return base

    return next(reversed(probabilities))


def evolve_sequence(
    sequence: str,
    *,
    distance: float,
    rng: random.Random,
    kappa: float = 2.0,
    pseudocount: float = 0.5,
) -> tuple[str, dict[str, int | float]]:
    """Evolve a sequence to a rounded target p-distance."""
    if not 0.0 <= distance <= 1.0:
        raise ValueError("distance must be between 0 and 1.")

    sequence = sequence.upper()
    eligible = [
        index
        for index, base in enumerate(sequence)
        if base in BASES
    ]

    if not eligible:
        raise ValueError(
            "Sequence contains no unambiguous DNA bases (A, C, G, T)."
        )

    matrix = estimate_substitution_matrix(
        sequence,
        kappa=kappa,
        pseudocount=pseudocount,
    )

    target_changes = round(distance * len(eligible))
    selected = rng.sample(eligible, target_changes)

    evolved = list(sequence)
    for index in selected:
        source = sequence[index]
        evolved[index] = _sample_base(matrix[source], rng)

    observed_changes = sum(
        sequence[index] != evolved[index]
        for index in eligible
    )
    observed_distance = observed_changes / len(eligible)

    metrics: dict[str, int | float] = {
        "sequence_length": len(sequence),
        "eligible_sites": len(eligible),
        "target_changes": target_changes,
        "observed_changes": observed_changes,
        "target_distance": distance,
        "observed_distance": observed_distance,
    }

    return "".join(evolved), metrics


def simulate_evolution(
    input_fasta: Path,
    output_fasta: Path,
    *,
    distance: float,
    replicates: int = 1,
    seed: int | None = None,
    kappa: float = 2.0,
    pseudocount: float = 0.5,
) -> Path:
    """Evolve each input record and write FASTA and metrics TSV."""
    if replicates < 1:
        raise ValueError("replicates must be at least 1.")
    if not 0.0 <= distance <= 1.0:
        raise ValueError("distance must be between 0 and 1.")

    records = list(read_fasta(input_fasta))
    if not records:
        raise ValueError(f"No FASTA records found in {input_fasta}")

    output_fasta = Path(output_fasta)
    output_fasta.parent.mkdir(parents=True, exist_ok=True)
    metrics_path = output_fasta.with_suffix(".evolution.tsv")

    rng = random.Random(seed)

    columns = [
        "original_id",
        "evolved_id",
        "replicate",
        "sequence_length",
        "eligible_sites",
        "target_changes",
        "observed_changes",
        "target_distance",
        "observed_distance",
        "seed",
        "kappa",
    ]

    with (
        output_fasta.open("w", encoding="utf-8", newline="\n") as fasta,
        metrics_path.open("w", encoding="utf-8", newline="") as table,
    ):
        writer = csv.DictWriter(
            table,
            fieldnames=columns,
            delimiter="\t",
        )
        writer.writeheader()

        for record_id, sequence in records:
            for replicate in range(1, replicates + 1):
                evolved, metrics = evolve_sequence(
                    sequence,
                    distance=distance,
                    rng=rng,
                    kappa=kappa,
                    pseudocount=pseudocount,
                )

                evolved_id = f"{record_id}|evolved_{replicate}"
                fasta.write(f">{evolved_id}\n")

                for start in range(0, len(evolved), 80):
                    fasta.write(evolved[start:start + 80] + "\n")

                writer.writerow({
                    "original_id": record_id,
                    "evolved_id": evolved_id,
                    "replicate": replicate,
                    **metrics,
                    "seed": seed,
                    "kappa": kappa,
                })

    return output_fasta


__all__ = [
    "read_fasta",
    "estimate_substitution_matrix",
    "evolve_sequence",
    "simulate_evolution",
]
