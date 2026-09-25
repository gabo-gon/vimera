"""Synthetic community construction."""

from __future__ import annotations

from dataclasses import dataclass

from vimera.config.models import SimulationConfig
from vimera.synthetic.background import build_background_groups
from vimera.synthetic.targets import (
    ResolvedTarget,
    resolve_background,
    resolve_targets,
)


@dataclass(frozen=True)
class ResolvedBackground:
    """A resolved background component."""

    group: str
    taxid: int
    abundance: float
    references: tuple


@dataclass(frozen=True)
class Community:
    """Resolved synthetic community."""

    targets: tuple[ResolvedTarget, ...]
    backgrounds: tuple[ResolvedBackground, ...] = ()

    def total_target_abundance(self) -> float:
        """Return total configured target abundance."""

        return sum(
            target.abundance
            for target in self.targets
        )

    def total_background_abundance(self) -> float:
        """Return total configured background abundance."""

        return sum(
            background.abundance
            for background in self.backgrounds
        )


def build_community(
    config: SimulationConfig,
) -> Community:
    """Resolve all references needed for a simulation."""

    targets = resolve_targets(
        targets=config.targets,
        reference_config=config.reference,
        seed=config.sequencing.seed,
    )

    backgrounds: list[ResolvedBackground] = []

    background_groups = build_background_groups(
        config.background
    )

    for group in background_groups:
        if not group.taxids or group.abundance <= 0:
            continue

        abundance_per_taxid = (
            group.abundance / len(group.taxids)
        )

        for taxid in group.taxids:
            resolved = resolve_background(
                taxid=taxid,
                abundance=abundance_per_taxid,
                reference_config=config.reference,
                seed=config.sequencing.seed,
            )

            backgrounds.append(
                ResolvedBackground(
                    group=group.name,
                    taxid=taxid,
                    abundance=abundance_per_taxid,
                    references=resolved.references,
                )
            )

    return Community(
        targets=tuple(targets),
        backgrounds=tuple(backgrounds),
    )