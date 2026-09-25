"""Target reference resolution for synthetic communities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vimera.config.models import (
    GenomeSelection,
    ReferenceConfig,
    Target,
)
from vimera.synthetic.genome_selection import (
    ReferenceRecord,
    resolve_references,
    select_references,
)


@dataclass(frozen=True)
class ResolvedTarget:
    """A configured target with resolved genome references."""

    taxid: int
    abundance: float
    references: tuple[ReferenceRecord, ...]


def resolve_target(
    target: Target,
    reference_config: ReferenceConfig,
    *,
    seed: int | None = None,
) -> ResolvedTarget:
    """Resolve genomes for one target."""

    references = resolve_references(
        taxid=target.taxid,
        cache_dir=reference_config.cache_dir,
        source=reference_config.source,
        refresh=reference_config.refresh,
        max_genomes=reference_config.max_genomes,
        batch_size=reference_config.batch_size,
    )

    selected = select_references(
        references,
        target.genome_selection,
        seed=seed,
    )

    return ResolvedTarget(
        taxid=target.taxid,
        abundance=target.abundance,
        references=tuple(selected),
    )

def resolve_targets(
    targets: list[Target],
    reference_config: ReferenceConfig,
    *,
    seed: int | None = None,
) -> list[ResolvedTarget]:
    """Resolve genomes for all configured targets."""

    return [
        resolve_target(
            target,
            reference_config,
            seed=seed,
        )
        for target in targets
    ]

def resolve_background(
    taxid: int,
    abundance: float,
    reference_config: ReferenceConfig,
    *,
    seed: int | None = None,
) -> ResolvedTarget:
    """Resolve references for one background TaxID."""

    references = resolve_references(
        taxid=taxid,
        cache_dir=reference_config.cache_dir,
        source=reference_config.source,
        refresh=reference_config.refresh,
        max_genomes=reference_config.max_genomes,
        batch_size=reference_config.batch_size,
    )

    selected = select_references(
        references,
        GenomeSelection.REFERENCE,
        seed=seed,
    )

    return ResolvedTarget(
        taxid=taxid,
        abundance=abundance,
        references=tuple(selected),
    )