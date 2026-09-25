"""Synthetic virome benchmark generation."""

from vimera.synthetic.benchmark import (
    prepare_benchmark,
    run_benchmark,
)
from vimera.synthetic.genome_selection import (
    ReferenceRecord,
)

__all__ = [
    "ReferenceRecord",
    "prepare_benchmark",
    "run_benchmark",
]