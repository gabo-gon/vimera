"""Native Illumina paired-end sequencing simulator.

This backend performs read simulation entirely in Python and does not
depend on ART, InSilicoSeq, WGSIM, pysam, or other external simulators.

The simulator:
    1. Allocates read pairs according to community abundance.
    2. Samples fragments from reference genomes.
    3. Generates paired-end reads.
    4. Applies an Illumina-like position-dependent substitution model.
    5. Generates matching Phred quality strings.
    6. Writes native FASTQ files.

The implementation is intentionally deterministic when ``config.seed`` is
provided.
"""

from __future__ import annotations

import math
import random
import shutil
from pathlib import Path
from typing import Iterable

from vimera.config.models import SequencingConfig
from vimera.synthetic.abundance import reads_for_abundance
from vimera.synthetic.community import Community
from vimera.synthetic.dataset import Dataset


DNA_BASES = "ACGT"

# Default Illumina-like sequencing error parameters.
#
# These are intentionally conservative defaults rather than an attempt
# to reproduce a specific historical Illumina instrument exactly.
DEFAULT_SUBSTITUTION_RATE = 0.001
DEFAULT_INDEL_RATE = 0.0

# Quality score bounds.
MIN_PHRED = 2
MAX_PHRED = 40

# Fragment lengths must be long enough to contain both reads.
MIN_FRAGMENT_LENGTH = 2


class IlluminaSimulator:
    """Native Python Illumina paired-end simulator."""

    name = "illumina"

    def __init__(
        self,
        executable: str | Path | None = None,
    ) -> None:
        """Initialize the native Illumina simulator.

        ``executable`` is retained for backwards compatibility with the
        previous ART-based constructor, but is intentionally ignored.
        """
        self.executable = (
            Path(executable)
            if executable is not None
            else None
        )

    # ------------------------------------------------------------------
    # FASTA
    # ------------------------------------------------------------------

    @staticmethod
    def _read_fasta(path: Path) -> str:
        """Read a FASTA file and return the concatenated sequence.

        FASTA line wrapping is irrelevant: all non-header lines are
        concatenated into one reference sequence.
        """

        if not path.is_file():
            raise FileNotFoundError(
                f"Reference FASTA does not exist: {path}"
            )

        sequence_parts: list[str] = []

        with path.open(
            "r",
            encoding="utf-8",
        ) as handle:
            for line in handle:
                line = line.strip()

                if not line:
                    continue

                if line.startswith(">"):
                    continue

                sequence_parts.append(line)

        sequence = "".join(sequence_parts).upper()

        if not sequence:
            raise ValueError(
                f"Reference FASTA contains no sequence: {path}"
            )

        invalid = set(sequence) - set("ACGTN")

        if invalid:
            raise ValueError(
                "Reference FASTA contains unsupported nucleotide "
                f"characters {sorted(invalid)}: {path}"
            )

        return sequence

    # ------------------------------------------------------------------
    # Abundance allocation
    # ------------------------------------------------------------------

    @staticmethod
    def _allocate_reads(
        total_reads: int,
        n_references: int,
    ) -> list[int]:
        """Allocate reads evenly across references.

        Any remainder is assigned deterministically to the first
        references.
        """

        if total_reads < 0:
            raise ValueError(
                "total_reads must not be negative."
            )

        if n_references <= 0:
            raise ValueError(
                "n_references must be positive."
            )

        base = total_reads // n_references
        remainder = total_reads % n_references

        return [
            base + (1 if index < remainder else 0)
            for index in range(n_references)
        ]

    # ------------------------------------------------------------------
    # Randomness
    # ------------------------------------------------------------------

    @staticmethod
    def _make_rng(
        seed: int | None,
        replicate: int,
        taxid: int,
        reference_index: int,
    ) -> random.Random:
        """Create a deterministic RNG for one reference."""

        if seed is None:
            return random.Random()

        derived_seed = (
            seed
            + replicate * 1_000_003
            + taxid * 1_009
            + reference_index * 101
        )

        return random.Random(derived_seed)

    # ------------------------------------------------------------------
    # Fragment generation
    # ------------------------------------------------------------------

    @staticmethod
    def _sample_fragment_length(
        rng: random.Random,
        mean: float,
        sd: float,
    ) -> int:
        """Sample a fragment length from a normal distribution."""

        if sd < 0:
            raise ValueError(
                "fragment_sd must not be negative."
            )

        if mean <= 0:
            raise ValueError(
                "fragment_mean must be positive."
            )

        if sd == 0:
            return max(
                MIN_FRAGMENT_LENGTH,
                int(round(mean)),
            )

        length = int(
            round(
                rng.gauss(
                    mean,
                    sd,
                )
            )
        )

        return max(
            MIN_FRAGMENT_LENGTH,
            length,
        )

    @staticmethod
    def _sample_fragment(
        sequence: str,
        fragment_length: int,
        read_length: int,
        rng: random.Random,
    ) -> tuple[str, str, int]:
        """Sample one paired-end fragment.

        Returns:
            R1 reference sequence,
            R2 reference sequence in sequencing orientation,
            zero-based fragment start.
        """

        sequence_length = len(sequence)

        if sequence_length < read_length:
            raise ValueError(
                "Reference sequence is shorter than the requested "
                f"read length ({sequence_length} < {read_length})."
            )

        fragment_length = max(
            fragment_length,
            2 * read_length,
        )

        if fragment_length > sequence_length:
            fragment_length = sequence_length

        max_start = sequence_length - fragment_length

        start = (
            rng.randint(
                0,
                max_start,
            )
            if max_start > 0
            else 0
        )

        fragment = sequence[
            start : start + fragment_length
        ]

        r1 = fragment[:read_length]

        r2_reference = fragment[-read_length:]

        r2 = IlluminaSimulator._reverse_complement(
            r2_reference
        )

        return r1, r2, start

    # ------------------------------------------------------------------
    # DNA
    # ------------------------------------------------------------------

    @staticmethod
    def _reverse_complement(sequence: str) -> str:
        """Return the reverse complement of a DNA sequence."""

        complement = str.maketrans(
            "ACGTN",
            "TGCAN",
        )

        return sequence.translate(
            complement
        )[::-1]

    # ------------------------------------------------------------------
    # Error model
    # ------------------------------------------------------------------

    @staticmethod
    def _error_probability(
        position: int,
        read_length: int,
        substitution_rate: float,
    ) -> float:
        """Return a position-dependent Illumina-like error probability.

        The error probability gradually increases toward the 3' end.

        ``substitution_rate`` is interpreted as the approximate mean
        substitution probability across the read.
        """

        if read_length <= 1:
            return substitution_rate

        fraction = position / (read_length - 1)

        # Mild 3'-end degradation.
        multiplier = 0.65 + 0.70 * fraction

        probability = (
            substitution_rate * multiplier
        )

        return min(
            max(probability, 0.0),
            0.25,
        )

    @staticmethod
    def _mutate_base(
        base: str,
        rng: random.Random,
    ) -> str:
        """Substitute a DNA base with one of the other bases."""

        if base not in DNA_BASES:
            return base

        alternatives = [
            candidate
            for candidate in DNA_BASES
            if candidate != base
        ]

        return rng.choice(alternatives)

    @classmethod
    def _simulate_read(
        cls,
        reference_read: str,
        rng: random.Random,
        substitution_rate: float,
    ) -> tuple[str, str]:
        """Generate one noisy read and its Phred quality string."""

        read_length = len(reference_read)

        sequence: list[str] = []
        qualities: list[str] = []

        for position, base in enumerate(reference_read):
            probability = cls._error_probability(
                position=position,
                read_length=read_length,
                substitution_rate=substitution_rate,
            )

            if base == "N":
                error = False
            else:
                error = (
                    rng.random() < probability
                )

            if error:
                observed = cls._mutate_base(
                    base,
                    rng,
                )

                # Convert the actual simulated error probability
                # into a Phred-like score.
                phred = max(
                    MIN_PHRED,
                    int(
                        round(
                            -10.0
                            * math.log10(
                                max(
                                    probability,
                                    1e-12,
                                )
                            )
                        )
                    ),
                )
            else:
                observed = base

                # Use a higher quality for correctly sequenced bases.
                phred = max(
                    MIN_PHRED,
                    int(
                        round(
                            -10.0
                            * math.log10(
                                max(
                                    probability * 0.1,
                                    1e-6,
                                )
                            )
                        ),
                    ),
                )

            phred = min(
                phred,
                MAX_PHRED,
            )

            sequence.append(observed)

            qualities.append(
                chr(phred + 33)
            )

        result_sequence = "".join(sequence)
        result_quality = "".join(qualities)

        # This should always be true because both strings are generated
        # from the same positions. Keep the assertion as a hard guard
        # against future changes.
        if len(result_sequence) != len(result_quality):
            raise RuntimeError(
                "Internal FASTQ generation error: "
                f"sequence length={len(result_sequence)}, "
                f"quality length={len(result_quality)}"
            )

        return (
            result_sequence,
            result_quality,
        )

    # ------------------------------------------------------------------
    # FASTQ
    # ------------------------------------------------------------------

    @staticmethod
    def _write_fastq_record(
        handle,
        read_id: str,
        sequence: str,
        quality: str,
    ) -> None:
        """Write one FASTQ record."""

        if len(sequence) != len(quality):
            raise ValueError(
                f"FASTQ sequence/quality length mismatch for "
                f"{read_id}: "
                f"{len(sequence)} vs {len(quality)}"
            )

        handle.write(
            f"@{read_id}\n"
        )
        handle.write(
            f"{sequence}\n"
        )
        handle.write(
            "+\n"
        )
        handle.write(
            f"{quality}\n"
        )

    # ------------------------------------------------------------------
    # Reference simulation
    # ------------------------------------------------------------------

    def _simulate_reference(
        self,
        reference_path: Path,
        number_of_reads: int,
        read_length: int,
        fragment_mean: float,
        fragment_sd: float,
        rng: random.Random,
        r1_handle,
        r2_handle,
        read_id_prefix: str,
        substitution_rate: float,
    ) -> None:
        """Generate paired reads from one reference."""

        sequence = self._read_fasta(
            reference_path
        )

        if len(sequence) < read_length:
            raise ValueError(
                f"Reference {reference_path} is only "
                f"{len(sequence)} nt long, but read length is "
                f"{read_length}."
            )

        for read_index in range(
            number_of_reads
        ):
            fragment_length = (
                self._sample_fragment_length(
                    rng=rng,
                    mean=fragment_mean,
                    sd=fragment_sd,
                )
            )

            r1_reference, r2_reference, start = (
                self._sample_fragment(
                    sequence=sequence,
                    fragment_length=fragment_length,
                    read_length=read_length,
                    rng=rng,
                )
            )

            r1_sequence, r1_quality = (
                self._simulate_read(
                    reference_read=r1_reference,
                    rng=rng,
                    substitution_rate=substitution_rate,
                )
            )

            r2_sequence, r2_quality = (
                self._simulate_read(
                    reference_read=r2_reference,
                    rng=rng,
                    substitution_rate=substitution_rate,
                )
            )

            fragment_end = (
                start
                + min(
                    fragment_length,
                    len(sequence),
                )
            )

            read_id = (
                f"{read_id_prefix}"
                f"_{read_index + 1:08d}"
                f"_start{start}"
                f"_end{fragment_end}"
            )

            self._write_fastq_record(
                r1_handle,
                f"{read_id}/1",
                r1_sequence,
                r1_quality,
            )

            self._write_fastq_record(
                r2_handle,
                f"{read_id}/2",
                r2_sequence,
                r2_quality,
            )

    # ------------------------------------------------------------------
    # Main simulation
    # ------------------------------------------------------------------

    def simulate(
        self,
        community: Community,
        config: SequencingConfig,
        output_dir: Path,
        replicate: int,
    ) -> Dataset:
        """Generate one native Illumina sequencing dataset."""

        if not community.targets:
            raise ValueError(
                "Cannot simulate an empty synthetic community."
            )

        if not config.paired_end:
            raise NotImplementedError(
                "The native Illumina backend currently supports "
                "paired-end simulation only."
            )

        read_length = (
            config.read_length
            if config.read_length is not None
            else 125
        )

        if read_length <= 0:
            raise ValueError(
                "read_length must be positive."
            )

        output_dir = Path(
            output_dir
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        replicate_dir = (
            output_dir
            / f"replicate_{replicate}"
        )

        replicate_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        fastq_r1 = (
            replicate_dir
            / "reads_R1.fastq"
        )

        fastq_r2 = (
            replicate_dir
            / "reads_R2.fastq"
        )

        components = []

        for target in community.targets:
            components.append(
                (
                    "target",
                    target.taxid,
                    target.abundance,
                    target.references,
                )
            )

        for background in community.backgrounds:
            components.append(
                (
                    background.group,
                    background.taxid,
                    background.abundance,
                    background.references,
                )
            )

        total_generated = 0

        with (
            fastq_r1.open(
                "w",
                encoding="utf-8",
                newline="\n",
            ) as r1_handle,
            fastq_r2.open(
                "w",
                encoding="utf-8",
                newline="\n",
            ) as r2_handle,
        ):

            for (
                group,
                taxid,
                abundance,
                references,
            ) in components:

                component_reads = (
                    reads_for_abundance(
                        config.reads,
                        abundance,
                    )
                )

                if component_reads <= 0:
                    continue

                if not references:
                    raise ValueError(
                        f"{group} TaxID {taxid} has no "
                        "resolved references."
                    )

                read_allocation = (
                    self._allocate_reads(
                        total_reads=component_reads,
                        n_references=len(
                            references
                        ),
                    )
                )

                for reference_index, (
                    reference,
                    reference_reads,
                ) in enumerate(
                    zip(
                        references,
                        read_allocation,
                    )
                ):
                    if reference_reads <= 0:
                        continue

                    reference_path = Path(
                        reference.fasta_path
                    )

                    rng = self._make_rng(
                        seed=config.seed,
                        replicate=replicate,
                        taxid=taxid,
                        reference_index=reference_index,
                    )

                    prefix = (
                        f"{group}_"
                        f"taxid_{taxid}_"
                        f"{reference.accession}"
                    )

                    self._simulate_reference(
                        reference_path=reference_path,
                        number_of_reads=reference_reads,
                        read_length=read_length,
                        fragment_mean=config.fragment_mean,
                        fragment_sd=config.fragment_sd,
                        rng=rng,
                        r1_handle=r1_handle,
                        r2_handle=r2_handle,
                        read_id_prefix=prefix,
                        substitution_rate=(
                            DEFAULT_SUBSTITUTION_RATE
                        ),
                    )

                    total_generated += (
                        reference_reads
                    )

        if total_generated <= 0:
            raise RuntimeError(
                "Native Illumina simulation generated no reads. "
                "Check target abundances and read count."
            )

        return Dataset(
            replicate=replicate,
            platform=self.name,
            fastq_r1=fastq_r1,
            fastq_r2=fastq_r2,
        )


__all__ = [
    "IlluminaSimulator",
]