"""Abundance calculations for synthetic communities."""

from __future__ import annotations

from collections.abc import Sequence


def validate_abundances(
    abundances: Sequence[float],
) -> None:
    """Validate abundance fractions."""

    for abundance in abundances:
        if abundance <= 0 or abundance > 1:
            raise ValueError(
                "Abundances must be greater than 0 and at most 1."
            )


def normalize_abundances(
    abundances: Sequence[float],
) -> list[float]:
    """Normalize abundances so they sum to one."""

    validate_abundances(abundances)

    total = sum(abundances)

    if total <= 0:
        raise ValueError(
            "Total abundance must be greater than zero."
        )

    return [
        abundance / total
        for abundance in abundances
    ]


def reads_for_abundance(
    total_reads: int,
    abundance: float,
) -> int:
    """Convert an abundance fraction into an integer read count."""

    if total_reads <= 0:
        raise ValueError(
            "total_reads must be positive."
        )

    if abundance <= 0 or abundance > 1:
        raise ValueError(
            "Abundance must be greater than 0 and at most 1."
        )

    return round(total_reads * abundance)