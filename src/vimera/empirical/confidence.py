"""Empirical confidence calculations for VIMERA.

This module contains the scientific/statistical implementation used by
the CLI confidence command.

The CLI layer should handle argument parsing, configuration, and output.
This module should operate only on data and return statistical results.
"""

from __future__ import annotations

from typing import Sequence


def calculate_empirical_confidence(
    observed_score: float,
    null_scores: Sequence[float],
    *,
    higher_is_better: bool = True,
) -> float:
    """Calculate an empirical confidence value from a null distribution.

    Parameters
    ----------
    observed_score:
        The score observed for the sample or candidate being evaluated.

    null_scores:
        Scores obtained from the empirical target-absent/null distribution.

    higher_is_better:
        If True, larger scores represent stronger evidence for the target.
        If False, smaller scores represent stronger evidence.

    Returns
    -------
    float
        Empirical confidence in the range [0, 1].

    Notes
    -----
    For ``higher_is_better=True``, confidence is calculated as:

        fraction(null_scores <= observed_score)

    For ``higher_is_better=False``:

        fraction(null_scores >= observed_score)

    A small-sample correction is used so that the returned value never
    becomes exactly zero:

        (count + 1) / (n + 1)

    This is useful when the observed score exceeds every null observation.
    """

    if not null_scores:
        raise ValueError("null_scores must contain at least one value.")

    values = [float(score) for score in null_scores]

    if higher_is_better:
        count = sum(score <= observed_score for score in values)
    else:
        count = sum(score >= observed_score for score in values)

    return (count + 1) / (len(values) + 1)


def empirical_p_value(
    observed_score: float,
    null_scores: Sequence[float],
    *,
    higher_is_better: bool = True,
) -> float:
    """Calculate an empirical one-sided p-value.

    Parameters
    ----------
    observed_score:
        Observed score to evaluate.

    null_scores:
        Scores from the empirical null distribution.

    higher_is_better:
        If True, unusually high scores are considered significant.
        If False, unusually low scores are considered significant.

    Returns
    -------
    float
        Empirical p-value.
    """

    if not null_scores:
        raise ValueError("null_scores must contain at least one value.")

    values = [float(score) for score in null_scores]

    if higher_is_better:
        extreme = sum(score >= observed_score for score in values)
    else:
        extreme = sum(score <= observed_score for score in values)

    return (extreme + 1) / (len(values) + 1)


def empirical_percentile(
    observed_score: float,
    null_scores: Sequence[float],
) -> float:
    """Return the empirical percentile of an observed score.

    Parameters
    ----------
    observed_score:
        Score being evaluated.

    null_scores:
        Empirical null distribution.

    Returns
    -------
    float
        Percentile in the range [0, 100].
    """

    if not null_scores:
        raise ValueError("null_scores must contain at least one value.")

    values = [float(score) for score in null_scores]

    count = sum(score <= observed_score for score in values)

    return 100.0 * count / len(values)