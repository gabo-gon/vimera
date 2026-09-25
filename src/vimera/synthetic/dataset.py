"""Synthetic dataset representation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Dataset:
    """A generated sequencing dataset."""

    replicate: int
    platform: str

    fastq_r1: Path | None = None
    fastq_r2: Path | None = None

    truth_path: Path | None = None
    abundance_path: Path | None = None

    def to_dict(self) -> dict:
        """Return a serializable representation."""

        return {
            "replicate": self.replicate,
            "platform": self.platform,
            "fastq_r1": (
                str(self.fastq_r1)
                if self.fastq_r1
                else None
            ),
            "fastq_r2": (
                str(self.fastq_r2)
                if self.fastq_r2
                else None
            ),
            "truth_path": (
                str(self.truth_path)
                if self.truth_path
                else None
            ),
            "abundance_path": (
                str(self.abundance_path)
                if self.abundance_path
                else None
            ),
        }