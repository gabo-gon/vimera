
import random

import pytest

from vimera.synthetic.evolution import (
    estimate_substitution_matrix,
    evolve_sequence,
    read_fasta,
    simulate_evolution,
)


def test_matrix_rows_sum_to_one():
    matrix = estimate_substitution_matrix("AACCGGTT")

    for source, probabilities in matrix.items():
        assert sum(probabilities.values()) == pytest.approx(1.0)
        assert source not in probabilities


def test_transition_weight_is_higher():
    matrix = estimate_substitution_matrix(
        "A" * 100 + "C" * 100 + "G" * 100 + "T" * 100,
        kappa=2.0,
    )

    # Equal nucleotide composition means transitions receive twice
    # the probability of each individual transversion.
    assert matrix["A"]["G"] == pytest.approx(
        2 * matrix["A"]["C"]
    )


def test_zero_distance_preserves_sequence():
    sequence = "ACGTNNACGT"

    evolved, metrics = evolve_sequence(
        sequence,
        distance=0.0,
        rng=random.Random(42),
    )

    assert evolved == sequence
    assert metrics["observed_changes"] == 0
    assert metrics["observed_distance"] == 0.0


def test_exact_rounded_number_of_sites_changes():
    sequence = "A" * 1000 + "NN"

    evolved, metrics = evolve_sequence(
        sequence,
        distance=0.01,
        rng=random.Random(42),
    )

    assert len(evolved) == len(sequence)
    assert evolved[-2:] == "NN"
    assert metrics["eligible_sites"] == 1000
    assert metrics["observed_changes"] == 10
    assert metrics["observed_distance"] == pytest.approx(0.01)


def test_reproducible_with_same_seed():
    sequence = "ACGT" * 100

    first, _ = evolve_sequence(
        sequence,
        distance=0.15,
        rng=random.Random(123),
    )
    second, _ = evolve_sequence(
        sequence,
        distance=0.15,
        rng=random.Random(123),
    )

    assert first == second


def test_invalid_distance_is_rejected():
    with pytest.raises(ValueError):
        evolve_sequence(
            "ACGT",
            distance=1.1,
            rng=random.Random(42),
        )


def test_fasta_supports_different_sequence_lengths(tmp_path):
    fasta = tmp_path / "input.fasta"
    fasta.write_text(
        ">seq1 description\nACGTACGT\n"
        ">seq2\nACGT\n",
        encoding="utf-8",
    )

    assert list(read_fasta(fasta)) == [
        ("seq1", "ACGTACGT"),
        ("seq2", "ACGT"),
    ]


def test_simulation_writes_fasta_and_metrics(tmp_path):
    input_fasta = tmp_path / "input.fasta"
    output_fasta = tmp_path / "evolved.fasta"

    input_fasta.write_text(
        ">virus_a\nACGT" * 0 + ">virus_a\n" + "ACGT" * 25
        + "\n>virus_b\n" + "TGCA" * 20 + "\n",
        encoding="utf-8",
    )

    result = simulate_evolution(
        input_fasta,
        output_fasta,
        distance=0.1,
        replicates=2,
        seed=42,
    )

    assert result.is_file()
    assert result.with_suffix(".evolution.tsv").is_file()

    records = list(read_fasta(result))
    assert len(records) == 4
    assert records[0][0] == "virus_a|evolved_1"
    assert records[1][0] == "virus_a|evolved_2"
