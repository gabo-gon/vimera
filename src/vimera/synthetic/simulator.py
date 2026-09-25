"""Common interface for sequencing simulators."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from vimera.config.models import SequencingConfig
from vimera.synthetic.community import Community
from vimera.synthetic.dataset import Dataset


class SequencingSimulator(Protocol):
    """Protocol implemented by sequencing backends."""

    def simulate(
        self,
        community: Community,
        config: SequencingConfig,
        output_dir: Path,
        replicate: int,
    ) -> Dataset:
        """Generate one sequencing dataset."""
        ...


def get_simulator(platform: str):
    """Return the simulator backend for a platform."""

    platform = platform.lower()

    if platform == "illumina":
        from vimera.synthetic.illumina import (
            IlluminaSimulator,
        )

        return IlluminaSimulator()

    if platform == "ont":
        from vimera.synthetic.ont import (
            ONTSimulator,
        )

        return ONTSimulator()

    raise ValueError(
        f"Unsupported sequencing platform: {platform}"
    )