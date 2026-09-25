"""NCBI reference cache utilities."""

from __future__ import annotations

from pathlib import Path


def reference_directory(
    cache_dir: Path,
    taxid: int,
    domain: str = "viral",
) -> Path:
    """Return the global cache directory for a taxon."""

    return Path(cache_dir) / domain / str(taxid)