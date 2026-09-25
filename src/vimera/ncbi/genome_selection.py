"""NCBI reference genome resolution and caching."""

from __future__ import annotations

import shutil
from pathlib import Path

from vimera.ncbi.datasets import (
    NCBIDatasetsError,
    download_virus_genomes,
)

from vimera.ncbi.metadata import (
    ReferenceRecord,
    _extract_refseq_status,
)

from vimera.synthetic.genome_selection import reference_directory

def _is_refseq_accession(accession: str) -> bool:
    """Return True when an accession uses a RefSeq accession prefix."""
    prefixes = (
        "NC_",
        "NG_",
        "NM_",
        "NR_",
        "NT_",
        "NW_",
        "WP_",
    )
    return accession.upper().startswith(prefixes)

def resolve_ncbi_references(
    taxid: int,
    cache_dir: Path,
    *,
    refresh: bool = False,
    refseq: bool = False,
    complete_only: bool = False,
    host: str | None = None,
    geo_location: str | None = None,
    max_genomes: int = 10,
    batch_size: int = 100,
) -> list[ReferenceRecord]:
    """Resolve viral references from NCBI and cache them locally."""
    if max_genomes < 1:
        raise ValueError("max_genomes must be at least 1.")

    if batch_size < 1:
        raise ValueError("batch_size must be at least 1.")
    if taxid <= 0:
        raise ValueError("TaxID must be positive.")

    cache_dir = Path(cache_dir)

    taxon_dir = reference_directory(
        cache_dir=cache_dir,
        taxid=taxid,
        domain="viral",
    )

    sequences_dir = taxon_dir / "sequences"

    sequences_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not refresh:
        cached = _load_cached_references(
            taxon_dir=taxon_dir,
            taxid=taxid,
        )

        if cached:
            return cached

    # Remove stale sequence files when refreshing.
    if refresh and sequences_dir.exists():
        for path in sequences_dir.iterdir():
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)

    download_dir = taxon_dir / "_download"

    if download_dir.exists():
        shutil.rmtree(download_dir)

    download_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        fasta_path = download_virus_genomes(
            taxid=taxid,
            output_dir=download_dir,
            refseq=refseq,
            complete_only=complete_only,
            host=host,
            geo_location=geo_location,
            max_genomes=max_genomes,
            batch_size=batch_size,
        )

        references = _split_fasta_records(
            fasta_path=fasta_path,
            sequences_dir=sequences_dir,
            taxid=taxid,
        )

    except NCBIDatasetsError:
        raise

    finally:
        shutil.rmtree(
            download_dir,
            ignore_errors=True,
        )

    if not references:
        raise RuntimeError(
            f"NCBI returned no usable reference genomes "
            f"for TaxID {taxid}."
        )

    _write_manifest(
        taxon_dir=taxon_dir,
        references=references,
    )

    return references


def _load_cached_references(
    taxon_dir: Path,
    taxid: int,
) -> list[ReferenceRecord]:
    """Load references from an existing local cache."""

    sequences_dir = taxon_dir / "sequences"

    if not sequences_dir.exists():
        return []

    records: list[ReferenceRecord] = []

    for path in sorted(
        list(sequences_dir.glob("*.fasta"))
        + list(sequences_dir.glob("*.fa"))
        + list(sequences_dir.glob("*.fna"))
    ):
        accession = path.stem

        sequence = "".join(
            line.strip()
            for line in path.read_text(
                encoding="utf-8"
            ).splitlines()
            if not line.startswith(">")
        )

        records.append(
            ReferenceRecord(
                accession=accession,
                taxid=taxid,
                fasta_path=path,
                source="ncbi",
                length=len(sequence),
                refseq=_extract_refseq_status(accession),
            )
        )

    return records


def _split_fasta_records(
    fasta_path: Path,
    sequences_dir: Path,
    taxid: int,
) -> list[ReferenceRecord]:
    """Split a multi-record FASTA into one file per accession."""

    sequences_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    records: list[ReferenceRecord] = []

    current_header: str | None = None
    current_sequence: list[str] = []

    def flush_record() -> None:
        if current_header is None:
            return

        accession = _accession_from_header(
            current_header
        )

        if not accession:
            return

        sequence = "".join(current_sequence).strip()

        if not sequence:
            return

        output_path = sequences_dir / f"{accession}.fasta"

        output_path.write_text(
            f">{current_header}\n"
            f"{_wrap_sequence(sequence)}\n",
            encoding="utf-8",
        )

        records.append(
            ReferenceRecord(
                accession=accession,
                taxid=taxid,
                fasta_path=output_path,
                source="ncbi",
                length=len(sequence),
                refseq=_is_refseq_accession(accession),
            )
        )

    with Path(fasta_path).open(
        "r",
        encoding="utf-8",
    ) as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n\r")

            if line.startswith(">"):
                flush_record()

                current_header = line[1:].strip()
                current_sequence = []

            elif line.strip():
                current_sequence.append(
                    line.strip()
                )

    flush_record()

    return records


def _accession_from_header(
    header: str,
) -> str:
    """Extract the accession from a FASTA header."""

    token = header.split()[0]

    # NCBI FASTA headers commonly look like:
    #
    #   NC_001477.1
    #   NC_001477.1|...
    #
    # Keep the accession/version when present.
    if "|" in token:
        token = token.split("|")[0]

    return token.strip()


def _wrap_sequence(
    sequence: str,
    width: int = 80,
) -> str:
    """Wrap a nucleotide sequence for FASTA output."""

    return "\n".join(
        sequence[index:index + width]
        for index in range(
            0,
            len(sequence),
            width,
        )
    )


def _write_manifest(
    taxon_dir: Path,
    references: list[ReferenceRecord],
) -> None:
    """Write a TSV manifest for cached references."""

    manifest = taxon_dir / "manifest.tsv"

    columns = [
        "accession",
        "taxid",
        "fasta_path",
        "source",
        "organism",
        "length",
        "is_complete",
        "host",
        "collection_date",
        "refseq",
    ]

    with manifest.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        handle.write(
            "\t".join(columns) + "\n"
        )

        for reference in references:
            values = reference.to_dict()

            handle.write(
                "\t".join(
                    str(values[column])
                    if values[column] is not None
                    else ""
                    for column in columns
                )
                + "\n"
            )