"""Resolution of local FASTA files into synthetic references."""

from __future__ import annotations

from pathlib import Path

from vimera.ncbi.models import ReferenceRecord


def resolve_fasta_references(
    fasta_path: Path,
) -> list[ReferenceRecord]:
    """Resolve every FASTA record in a local file.

    Each record becomes a separate reference. The original FASTA path is
    retained; simulators must select the matching record by accession.
    """
    fasta_path = Path(fasta_path).expanduser().resolve()

    if not fasta_path.is_file():
        raise FileNotFoundError(
            f"Target FASTA file does not exist: {fasta_path}"
        )

    references: list[ReferenceRecord] = []
    accession: str | None = None
    sequence_parts: list[str] = []
    seen_accessions: set[str] = set()

    def add_record() -> None:
        if accession is None:
            return

        sequence = "".join(sequence_parts).upper()
        if not sequence:
            raise ValueError(
                f"FASTA record {accession!r} has no sequence "
                f"in {fasta_path}."
            )

        references.append(
            ReferenceRecord(
                accession=accession,
                taxid=None,
                fasta_path=fasta_path,
                source="local_fasta",
                organism=None,
                length=len(sequence),
                is_complete=None,
                host=None,
                collection_date=None,
                refseq=None,
            )
        )

    with fasta_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()

            if not line:
                continue

            if line.startswith(">"):
                add_record()

                header = line[1:].strip()
                if not header:
                    raise ValueError(
                        f"Empty FASTA header at line {line_number} "
                        f"in {fasta_path}."
                    )

                accession = header.split()[0]
                if accession in seen_accessions:
                    raise ValueError(
                        f"Duplicate FASTA record ID {accession!r} "
                        f"in {fasta_path}. Record IDs must be unique "
                        "within each FASTA file."
                    )

                seen_accessions.add(accession)
                sequence_parts = []
                continue

            if accession is None:
                raise ValueError(
                    f"Sequence data before the first FASTA header "
                    f"at line {line_number} in {fasta_path}."
                )

            sequence_parts.append(line)

    add_record()

    if not references:
        raise ValueError(f"No FASTA records found in {fasta_path}.")

    return references


__all__ = ["resolve_fasta_references"]