"""Data models for NCBI reference genomes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReferenceRecord:
    """A genome reference available to VIMERA."""

    accession: str
    taxid: int | None
    fasta_path: Path

    source: str

    organism: str | None = None
    length: int | None = None
    is_complete: bool | None = None

    host: str | None = None
    collection_date: str | None = None

    refseq: bool | None = None

    def to_dict(self) -> dict:
        """Return a serializable representation."""

        return {
            "accession": self.accession,
            "taxid": self.taxid,
            "fasta_path": str(self.fasta_path),
            "source": self.source,
            "organism": self.organism,
            "length": self.length,
            "is_complete": self.is_complete,
            "host": self.host,
            "collection_date": self.collection_date,
            "refseq": self.refseq,
        }