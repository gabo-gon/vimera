"""Reference genome resolution for synthetic simulations."""

from __future__ import annotations

from pathlib import Path

from vimera.config.models import GenomeSelection, ReferenceSource
from vimera.ncbi.models import ReferenceRecord
from vimera.ncbi.metadata import (
    find_local_references,
    reference_directory,
    select_references,
)


def resolve_references(
    taxid: int,
    cache_dir: Path,
    *,
    source,
    refresh: bool = False,
    max_genomes: int = 10,
    batch_size: int = 100,
) -> list[ReferenceRecord]:
    """Resolve references from the global cache and/or NCBI."""

    if taxid <= 0:
        raise ValueError("TaxID must be positive.")

    cache_dir = Path(cache_dir).expanduser()

    local = find_local_references(
        cache_dir=cache_dir,
        taxid=taxid,
    )

    if source == ReferenceSource.LOCAL:
        if not local:
            raise FileNotFoundError(
                f"No local references found for TaxID {taxid} "
                f"in {reference_directory(cache_dir, taxid)}"
            )

        return local

    if source == ReferenceSource.AUTO and local and not refresh:
        return local

    if source in (
        ReferenceSource.AUTO,
        ReferenceSource.NCBI,
    ):
        from vimera.ncbi.genome_selection import (
            resolve_ncbi_references,
        )

        return resolve_ncbi_references(
            taxid=taxid,
            cache_dir=cache_dir,
            refresh=refresh,
            refseq=True,
            max_genomes=max_genomes,
            batch_size=batch_size,
        )

    raise ValueError(
        f"Unsupported reference source: {source}"
    )