"""Truth-table generation for synthetic datasets."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from vimera.synthetic.community import Community


TRUTH_COLUMNS = [
    "component",
    "category",
    "taxid",
    "abundance",
    "accession",
    "source",
    "fasta_path",
    "organism",
    "length",
    "is_complete",
    "host",
    "collection_date",
    "refseq",
]


def build_truth_table(
    community: Community,
) -> list[dict[str, Any]]:
    """Build a reference-level truth table."""

    rows: list[dict[str, Any]] = []

    for target in community.targets:
        for reference in target.references:
            rows.append(
                {
                    "component": "target",
                    "category": "target",
                    "taxid": target.taxid,
                    "abundance": target.abundance,
                    "accession": reference.accession,
                    "source": reference.source,
                    "fasta_path": str(reference.fasta_path),
                    "organism": reference.organism,
                    "length": reference.length,
                    "is_complete": reference.is_complete,
                    "host": reference.host,
                    "collection_date": reference.collection_date,
                    "refseq": reference.refseq,
                }
            )

    for background in community.backgrounds:
        for reference in background.references:
            rows.append(
                {
                    "component": "background",
                    "category": background.group,
                    "taxid": background.taxid,
                    "abundance": background.abundance,
                    "accession": reference.accession,
                    "source": reference.source,
                    "fasta_path": str(reference.fasta_path),
                    "organism": reference.organism,
                    "length": reference.length,
                    "is_complete": reference.is_complete,
                    "host": reference.host,
                    "collection_date": reference.collection_date,
                    "refseq": reference.refseq,
                }
            )

    return rows


def write_truth_table(
    community: Community,
    output_path: Path,
) -> Path:
    """Write the truth table as TSV."""

    output_path = Path(output_path)
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    rows = build_truth_table(community)

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=TRUTH_COLUMNS,
            delimiter="\t",
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(rows)

    return output_path


__all__ = [
    "TRUTH_COLUMNS",
    "build_truth_table",
    "write_truth_table",
]
