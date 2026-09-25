"""Reference metadata and cached genome records."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
import csv

from vimera.config.models import GenomeSelection


@dataclass(frozen=True)
class ReferenceRecord:
    """A genome reference available to VIMERA."""

    accession: str
    taxid: int
    fasta_path: Path

    source: str

    organism: str | None = None
    length: int | None = None
    is_complete: bool | None = None

    host: str | None = None
    collection_date: str | None = None

    refseq: bool | None = None

    def to_dict(self) -> dict[str, Any]:
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


def parse_jsonl_metadata(
    metadata_path: Path,
    *,
    taxid: int | None = None,
    fasta_directory: Path | None = None,
    default_taxid: int | None = None,
    source: str = "ncbi",
) -> list[ReferenceRecord]:
    """Parse NCBI-style JSONL metadata into ReferenceRecord objects.

    The parser intentionally tolerates missing optional metadata because
    different NCBI Datasets queries can return slightly different fields.
    """

    metadata_path = Path(metadata_path)

    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Metadata file not found: {metadata_path}"
        )

    records: list[ReferenceRecord] = []

    with metadata_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in {metadata_path} at line "
                    f"{line_number}: {exc}"
                ) from exc
            if default_taxid is None:
                default_taxid = taxid
            record = _parse_metadata_record(
                data,
                default_taxid=default_taxid,
                fasta_directory=fasta_directory,
                source=source,
            )

            if record is not None:
                records.append(record)

    return records


def _parse_metadata_record(
    data: dict[str, Any],
    *,
    default_taxid: int | None,
    fasta_directory: Path | None,
    source: str,
) -> ReferenceRecord | None:
    """Convert one NCBI metadata object into a ReferenceRecord."""

    accession = (
        data.get("accession")
        or data.get("accession_version")
        or data.get("assembly_accession")
    )

    if not accession:
        return None

    taxid = _extract_taxid(data)

    if taxid is None:
        taxid = default_taxid

    if taxid is None:
        return None

    fasta_path = _extract_fasta_path(data)

    if fasta_path is None:
        return None

    organism = _extract_organism(data)

    length = _extract_length(data)

    is_complete = _extract_complete_status(data)

    host = _extract_host(data)

    collection_date = _extract_collection_date(data)

    refseq = _extract_refseq_status(data)

    return ReferenceRecord(
        accession=str(accession),
        taxid=int(taxid),
        fasta_path=Path(fasta_path),
        source=source,
        organism=organism,
        length=length,
        is_complete=is_complete,
        host=host,
        collection_date=collection_date,
        refseq=refseq,
    )


def _extract_taxid(data: dict[str, Any]) -> int | None:
    """Extract TaxID from common NCBI metadata layouts."""

    candidates = [
        data.get("taxid"),
        data.get("tax_id"),
        data.get("organism", {}).get("tax_id")
        if isinstance(data.get("organism"), dict)
        else None,
    ]

    for value in candidates:
        if value is None:
            continue

        try:
            return int(value)
        except (TypeError, ValueError):
            continue

    return None


def _extract_fasta_path(data: dict[str, Any]) -> str | None:
    """Extract the cached FASTA path from metadata."""

    candidates = [
        data.get("fasta_path"),
        data.get("fasta"),
        data.get("fasta_file"),
        data.get("sequence", {}).get("fasta")
        if isinstance(data.get("sequence"), dict)
        else None,
    ]

    for value in candidates:
        if value:
            return str(value)

    return None


def _extract_organism(data: dict[str, Any]) -> str | None:
    """Extract organism name."""

    organism = data.get("organism")

    if isinstance(organism, str):
        return organism

    if isinstance(organism, dict):
        for key in ("organism_name", "name", "scientific_name"):
            value = organism.get(key)
            if value:
                return str(value)

    for key in ("organism_name", "scientific_name"):
        value = data.get(key)
        if value:
            return str(value)

    return None


def _extract_length(data: dict[str, Any]) -> int | None:
    """Extract genome length."""

    candidates = [
        data.get("length"),
        data.get("sequence_length"),
        data.get("sequence", {}).get("length")
        if isinstance(data.get("sequence"), dict)
        else None,
    ]

    for value in candidates:
        if value is None:
            continue

        try:
            return int(value)
        except (TypeError, ValueError):
            continue

    return None


def _extract_complete_status(data: dict[str, Any]) -> bool | None:
    """Extract complete-genome status."""

    candidates = [
        data.get("is_complete"),
        data.get("complete"),
        data.get("completeness"),
    ]

    for value in candidates:
        if isinstance(value, bool):
            return value

        if isinstance(value, str):
            normalized = value.strip().lower()

            if normalized in {"complete", "true", "yes"}:
                return True

            if normalized in {"partial", "incomplete", "false", "no"}:
                return False

    return None


def _extract_host(data: dict[str, Any]) -> str | None:
    """Extract host metadata."""

    host = data.get("host")

    if isinstance(host, str):
        return host

    if isinstance(host, dict):
        for key in ("name", "organism_name", "scientific_name"):
            value = host.get(key)
            if value:
                return str(value)

    return None


def _extract_collection_date(data: dict[str, Any]) -> str | None:
    """Extract collection date."""

    for key in (
        "collection_date",
        "collectionDate",
        "sample_collection_date",
    ):
        value = data.get(key)

        if value:
            return str(value)

    return None


def _extract_refseq_status(data: dict[str, Any]) -> bool | None:
    """Determine whether the record is a RefSeq reference."""

    refseq = data.get("refseq")

    if isinstance(refseq, bool):
        return refseq

    accession = str(
        data.get("accession")
        or data.get("accession_version")
        or ""
    )

    return accession.startswith(("NC_", "NG_", "NM_", "NR_", "NT_", "NW_", "WP_"))


def reference_directory(
    cache_dir: Path,
    taxid: int,
    domain: str = "viral",
) -> Path:
    """Return the global cache directory for a taxon."""

    return Path(cache_dir) / domain / str(taxid)


def find_local_references(
    cache_dir: Path,
    taxid: int,
    *,
    domain: str = "viral",
) -> list[ReferenceRecord]:
    """Find FASTA references already present in the global cache."""

    directory = reference_directory(
        cache_dir=cache_dir,
        taxid=taxid,
        domain=domain,
    )

    sequences_directory = directory / "sequences"

    if not sequences_directory.exists():
        return []

    manifest = directory / "manifest.tsv"

    # Prefer the manifest because it contains reference metadata.
    if manifest.exists():
        records: list[ReferenceRecord] = []

        with manifest.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")

            for row in reader:
                fasta_path = Path(row["fasta_path"])

                if not fasta_path.exists():
                    continue

                refseq_value = row.get("refseq")

                if refseq_value in {"True", "true", "1"}:
                    refseq = True
                elif refseq_value in {"False", "false", "0"}:
                    refseq = False
                else:
                    refseq = None

                records.append(
                    ReferenceRecord(
                        accession=row["accession"],
                        taxid=int(row["taxid"]),
                        fasta_path=fasta_path,
                        source=row.get("source") or "local",
                        organism=row.get("organism") or None,
                        length=(
                            int(row["length"])
                            if row.get("length")
                            else None
                        ),
                        is_complete=(
                            row["is_complete"] == "True"
                            if row.get("is_complete")
                            else None
                        ),
                        host=row.get("host") or None,
                        collection_date=(
                            row.get("collection_date") or None
                        ),
                        refseq=refseq,
                    )
                )

        if records:
            return records

    # Fallback for caches without a manifest.
    records = []

    for fasta_path in sorted(
        list(sequences_directory.glob("*.fasta"))
        + list(sequences_directory.glob("*.fa"))
        + list(sequences_directory.glob("*.fna"))
    ):
        accession = fasta_path.stem

        records.append(
            ReferenceRecord(
                accession=accession,
                taxid=taxid,
                fasta_path=fasta_path,
                source="local",
            )
        )

    return records


def select_references(
    references: Iterable[ReferenceRecord],
    strategy: GenomeSelection,
    *,
    seed: int | None = None,
) -> list[ReferenceRecord]:
    """Select references according to a genome-selection strategy."""

    refs = list(references)

    if not refs:
        raise ValueError("No reference genomes are available.")

    if strategy == GenomeSelection.ALL_COMPLETE:
        selected = [
            ref
            for ref in refs
            if ref.is_complete is True
        ]

        if not selected:
            raise ValueError(
                "Genome selection 'all_complete' was requested, "
                "but no complete references are available."
            )

        return selected

    if strategy == GenomeSelection.REFERENCE:
        refseq = [
            ref
            for ref in refs
            if ref.refseq is True
        ]

        return [refseq[0] if refseq else refs[0]]

    if strategy == GenomeSelection.RANDOM:
        import random

        rng = random.Random(seed)
        return [rng.choice(refs)]

    if strategy == GenomeSelection.DIVERSE:
        if len(refs) == 1:
            return refs

        refs_with_length = [
            ref
            for ref in refs
            if ref.length is not None
        ]

        if not refs_with_length:
            return [refs[0]]

        shortest = min(
            refs_with_length,
            key=lambda ref: ref.length,
        )

        longest = max(
            refs_with_length,
            key=lambda ref: ref.length,
        )

        if shortest.accession == longest.accession:
            return [shortest]

        return [shortest, longest]

    raise ValueError(
        f"Unsupported genome-selection strategy: {strategy}"
    )