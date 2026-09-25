"""Synthetic community background construction."""

from __future__ import annotations

from dataclasses import dataclass

from vimera.config.models import Background


@dataclass(frozen=True)
class BackgroundGroup:
    """One background taxonomic group."""

    name: str
    taxids: tuple[int, ...]
    abundance: float


def build_background_groups(
    background: Background,
) -> tuple[BackgroundGroup, ...]:
    """Divide background abundance equally among populated groups."""

    candidates = [
        ("host", background.host_taxids),
        ("bacterial", background.bacterial_taxids),
        ("viral", background.viral_taxids),
        ("near_neighbor", background.near_neighbor_taxids),
    ]

    populated = [
        (name, tuple(taxids))
        for name, taxids in candidates
        if taxids
    ]

    if not populated or background.abundance <= 0:
        return ()

    group_abundance = (
        background.abundance / len(populated)
    )

    return tuple(
        BackgroundGroup(
            name=name,
            taxids=taxids,
            abundance=group_abundance,
        )
        for name, taxids in populated
    )