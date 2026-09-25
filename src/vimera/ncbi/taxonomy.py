"""Small helpers for NCBI Taxonomy operations."""

from __future__ import annotations

import shutil
import subprocess


class NCBITaxonomyError(RuntimeError):
    """Raised when an NCBI taxonomy operation fails."""


def find_datasets() -> str:
    """Return the datasets executable path."""

    executable = shutil.which("datasets")

    if executable is None:
        raise NCBITaxonomyError(
            "NCBI Datasets executable 'datasets' was not found."
        )

    return executable


def validate_taxid(taxid: int) -> int:
    """Validate an NCBI Taxonomy ID."""

    if not isinstance(taxid, int):
        raise ValueError("TaxID must be an integer.")

    if taxid <= 0:
        raise ValueError("TaxID must be positive.")

    return taxid


def taxonomy_summary(taxid: int) -> str:
    """Return NCBI taxonomy information as JSON text."""

    validate_taxid(taxid)

    executable = find_datasets()

    command = [
        executable,
        "summary",
        "taxonomy",
        "taxon",
        str(taxid),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise NCBITaxonomyError(
            result.stderr.strip()
        )

    return result.stdout