"""Benchmark preparation and execution for synthetic virome datasets."""

from __future__ import annotations

from pathlib import Path

from vimera.config.models import SimulationConfig
from vimera.synthetic.community import Community, build_community
from vimera.synthetic.simulator import get_simulator
from vimera.synthetic.truth import write_truth_table


def prepare_benchmark(
    config: SimulationConfig,
) -> Community:
    """
    Resolve references and prepare the benchmark directory.

    This stage:

    1. Creates the experiment output directory.
    2. Resolves target references.
    3. Builds the synthetic community.
    4. Writes the reference/abundance truth table.

    Parameters
    ----------
    config:
        Fully resolved VIMERA simulation configuration.

    Returns
    -------
    Community
        Resolved synthetic community.
    """

    output_dir = (
        Path(config.output_dir)
        / config.experiment_name
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    community = build_community(config)

    truth_path = output_dir / "truth.tsv"

    write_truth_table(
        community,
        truth_path,
    )

    return community


def run_benchmark(
    config: SimulationConfig,
):
    """
    Prepare and execute a complete synthetic sequencing benchmark.

    Reference resolution and truth-table generation are performed first.
    The configured sequencing backend is then used to generate each
    replicate.
    """

    output_dir = (
        Path(config.output_dir)
        / config.experiment_name
    )

    community = prepare_benchmark(config)

    simulator = get_simulator(
        config.sequencing.platform.value
    )

    datasets = []

    for replicate in range(
        1,
        config.sequencing.replicates + 1,
    ):
        dataset = simulator.simulate(
            community=community,
            config=config.sequencing,
            output_dir=output_dir,
            replicate=replicate,
        )

        datasets.append(dataset)

    return datasets


__all__ = [
    "prepare_benchmark",
    "run_benchmark",
]
