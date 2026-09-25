"""NCBI Entrez-based reference genome retrieval."""

from __future__ import annotations

import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET


class NCBIDatasetsError(RuntimeError):
    """Raised when NCBI reference retrieval cannot complete."""


NCBI_EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _request(
    endpoint: str,
    params: dict[str, str],
) -> str:
    """Perform a request against NCBI E-utilities."""

    url = f"{NCBI_EUTILS}/{endpoint}?{urlencode(params)}"

    request = Request(
        url,
        headers={
            "User-Agent": "VIMERA/0.1 (synthetic virome benchmark)",
        },
    )

    try:
        with urlopen(request, timeout=60) as response:
            return response.read().decode("utf-8")

    except Exception as exc:
        raise NCBIDatasetsError(
            f"NCBI request failed: {exc}"
        ) from exc


def search_nucleotide(
    taxid: int,
    *,
    refseq: bool = False,
    complete_only: bool = False,
    host: str | None = None,
    geo_location: str | None = None,
    retmax: int = 10,
) -> list[str]:
    """Return nucleotide UIDs belonging to a TaxID."""

    if taxid <= 0:
        raise ValueError("TaxID must be positive.")

    if retmax < 1:
        raise ValueError("retmax must be at least 1.")

    terms = [
        f"txid{taxid}[Organism:exp]"
    ]

    if complete_only:
        terms.append('"complete genome"[Title]')

    if refseq:
        terms.append("srcdb_refseq[PROP]")

    if host:
        terms.append(f'"{host}"[All Fields]')

    if geo_location:
        terms.append(
            f'"{geo_location}"[All Fields]'
        )

    query = " AND ".join(
        f"({term})"
        for term in terms
    )

    print(
        "\nVIMERA NCBI ESearch:"
        f"\n  taxid: {taxid}"
        f"\n  retmax: {retmax}"
        f"\n  query: {query}"
    )

    xml = _request(
        "esearch.fcgi",
        {
            "db": "nuccore",
            "term": query,
            "retmode": "xml",
            "retmax": str(retmax),
            "idtype": "acc",
        },
    )

    root = ET.fromstring(xml)

    accessions = [
        element.text
        for element in root.findall(".//Id")
        if element.text
    ]

    return accessions


def download_fasta(
    accessions: list[str],
    output_path: Path,
    *,
    batch_size: int = 100,
) -> Path:
    """Download nucleotide FASTA records from NCBI in batches."""

    if not accessions:
        raise NCBIDatasetsError(
            "No NCBI accessions were provided."
        )

    if batch_size < 1:
        raise ValueError(
            "batch_size must be at least 1."
        )

    output_path = Path(output_path)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    batches = [
        accessions[index:index + batch_size]
        for index in range(
            0,
            len(accessions),
            batch_size,
        )
    ]

    print(
        "\nVIMERA NCBI FASTA retrieval:"
        f"\n  genomes: {len(accessions)}"
        f"\n  batch_size: {batch_size}"
        f"\n  batches: {len(batches)}"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as output:

        for batch_number, batch in enumerate(
            batches,
            start=1,
        ):
            print(
                f"  Downloading batch "
                f"{batch_number}/{len(batches)} "
                f"({len(batch)} genomes)..."
            )

            time.sleep(0.34)

            fasta = _request(
                "efetch.fcgi",
                {
                    "db": "nuccore",
                    "id": ",".join(batch),
                    "rettype": "fasta",
                    "retmode": "text",
                },
            )

            if fasta.strip():
                output.write(fasta)

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise NCBIDatasetsError(
            "NCBI returned an empty FASTA response."
        )

    return output_path


def download_virus_genomes(
    taxid: int,
    output_dir: Path,
    *,
    refseq: bool = False,
    complete_only: bool = False,
    host: str | None = None,
    geo_location: str | None = None,
    max_genomes: int = 10,
    batch_size: int = 100,
) -> Path:
    """Download viral genomes for a TaxID from NCBI."""

    if max_genomes < 1:
        raise ValueError(
            "max_genomes must be at least 1."
        )

    if batch_size < 1:
        raise ValueError(
            "batch_size must be at least 1."
        )

    if taxid <= 0:
        raise ValueError(
            "TaxID must be positive."
        )

    output_dir = Path(output_dir)

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    print(
        "\nVIMERA NCBI request:"
        f"\n  taxid: {taxid}"
        f"\n  max_genomes: {max_genomes}"
        f"\n  batch_size: {batch_size}"
        f"\n  refseq: {refseq}"
        f"\n  complete_only: {complete_only}"
        f"\n  host: {host}"
        f"\n  geo_location: {geo_location}"
    )

    accessions = search_nucleotide(
        taxid=taxid,
        refseq=refseq,
        complete_only=complete_only,
        host=host,
        geo_location=geo_location,
        retmax=max_genomes,
    )

    if not accessions:
        raise NCBIDatasetsError(
            f"NCBI returned no nucleotide records "
            f"for TaxID {taxid}."
        )

    # Defensive limit in case NCBI returns more records
    # than requested.
    accessions = accessions[:max_genomes]

    print(
        f"\n  Selected {len(accessions)} genome(s)."
    )

    fasta_path = output_dir / "genomes.fasta"

    return download_fasta(
        accessions=accessions,
        output_path=fasta_path,
        batch_size=batch_size,
    )


def extract_dataset(
    zip_path: Path,
    output_dir: Path,
) -> None:
    """Compatibility shim.

    NCBI retrieval is now performed directly through
    E-utilities, so no dataset archive is produced.
    """

    raise NCBIDatasetsError(
        "extract_dataset() is no longer used by the "
        "Python-native NCBI retrieval backend."
    )


def find_genomic_fasta(
    dataset_dir: Path,
) -> list[Path]:
    """Find FASTA files in a directory."""

    dataset_dir = Path(dataset_dir)

    return sorted(
        list(dataset_dir.rglob("*.fna"))
        + list(dataset_dir.rglob("*.fasta"))
        + list(dataset_dir.rglob("*.fa"))
    )


def find_metadata_jsonl(
    dataset_dir: Path,
) -> list[Path]:
    """Compatibility shim for the former Datasets backend."""

    return sorted(
        Path(dataset_dir).rglob("*.jsonl")
    )