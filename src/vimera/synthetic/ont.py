"""Native Oxford Nanopore sequencing simulator.

This backend performs ONT-style read simulation entirely in Python and does
not depend on NanoSim, ART, InSilicoSeq, pysam, or other external simulators.

The simulator:

    1. Allocates reads according to community abundance.
    2. Samples read lengths from a truncated log-normal distribution.
    3. Samples fragments from reference genomes.
    4. Randomly selects the forward or reverse-complement strand.
    5. Applies an ONT-like substitution/insertion/deletion error model.
    6. Generates a matching Phred quality string.
    7. Writes native FASTQ files.

Default benchmark read-length profile:

    minimum read length : 200 nt
    median read length  : approximately 1,000 nt
    maximum read length : 10,000 nt

The read-length distribution is a VIMERA benchmark profile rather than
an exact representation of a particular ONT chemistry, basecaller, or
MinKNOW filtering configuration.

The implementation is deterministic when ``config.seed`` is provided.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from vimera.config.models import SequencingConfig
from vimera.synthetic.abundance import reads_for_abundance
from vimera.synthetic.community import Community
from vimera.synthetic.dataset import Dataset


DNA_BASES = "ACGT"


# ============================================================================
# Read-length model
# ============================================================================

DEFAULT_MIN_READ_LENGTH = 200
DEFAULT_MEDIAN_READ_LENGTH = 1_000
DEFAULT_MAX_READ_LENGTH = 10_000

# Width of the underlying log-normal distribution.
#
# A sigma of 1.0 gives a strongly right-skewed long-read distribution.
DEFAULT_READ_LENGTH_SIGMA = 1.0


# ============================================================================
# Error model
# ============================================================================

# Overall per-reference-base error probability.
#
# This is a benchmark parameter, not a claim about a particular ONT
# chemistry/basecaller combination.
DEFAULT_ERROR_RATE = 0.01

# Conditional distribution of error types.
#
# 20% insertions
# 30% deletions
# 50% substitutions
DEFAULT_INSERTION_FRACTION = 0.20
DEFAULT_DELETION_FRACTION = 0.30
DEFAULT_SUBSTITUTION_FRACTION = 0.50


# ============================================================================
# FASTQ quality model
# ============================================================================

MIN_PHRED = 2
MAX_PHRED = 30


class ONTSimulator:
    """Native Python Oxford Nanopore sequencing simulator."""

    name = "ont"

    # ------------------------------------------------------------------
    # FASTA
    # ------------------------------------------------------------------

    @staticmethod
    def _read_fasta(
        path: Path,
        accession: str | None = None,
    ) -> str:
        """Read a FASTA sequence, optionally selecting a specific record."""

        path = Path(path)

        if not path.is_file():
            raise FileNotFoundError(
                f"Reference FASTA does not exist: {path}"
            )

        records: dict[str, list[str]] = {}
        current_accession: str | None = None

        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                line = line.strip()

                if not line:
                    continue

                if line.startswith(">"):
                    header = line[1:].strip()
                    if not header:
                        raise ValueError(
                            f"Empty FASTA header at line {line_number} "
                            f"in {path}."
                        )

                    current_accession = header.split()[0]
                    if current_accession in records:
                        raise ValueError(
                            f"Duplicate FASTA record ID "
                            f"{current_accession!r} in {path}."
                        )

                    records[current_accession] = []
                    continue

                if current_accession is None:
                    raise ValueError(
                        f"Sequence data before the first FASTA header "
                        f"at line {line_number} in {path}."
                    )

                records[current_accession].append(line)

        if accession is not None:
            if accession not in records:
                raise ValueError(
                    f"FASTA record {accession!r} was not found in {path}."
                )
            sequence_parts = records[accession]
        else:
            if len(records) != 1:
                raise ValueError(
                    f"{path} contains {len(records)} FASTA records. "
                    "Specify an accession to select one record."
                )
            sequence_parts = next(iter(records.values()))

        sequence = "".join(sequence_parts).upper()

        if not sequence:
            raise ValueError(
                f"Reference FASTA contains an empty sequence: {path}"
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

        Example:

            10 reads / 3 references -> [4, 3, 3]
             2 reads / 5 references -> [1, 1, 0, 0, 0]
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
    # Read length
    # ------------------------------------------------------------------

    @staticmethod
    def _sample_read_length(
        rng: random.Random,
        minimum: int = DEFAULT_MIN_READ_LENGTH,
        median: int = DEFAULT_MEDIAN_READ_LENGTH,
        maximum: int = DEFAULT_MAX_READ_LENGTH,
        sigma: float = DEFAULT_READ_LENGTH_SIGMA,
    ) -> int:
        """Sample a read length from a truncated log-normal distribution.

        The underlying log-normal distribution has ``median`` as its
        untruncated median.

        Because explicit minimum and maximum limits truncate the
        distribution, the resulting median is not mathematically
        guaranteed to remain exactly equal to ``median``. The default
        parameters are chosen so that the resulting distribution remains
        centered around approximately 1 kb while retaining a long
        right-hand tail.

        Rejection sampling is used because the bounds are explicit and
        the expected rejection rate is manageable for the default
        parameters.
        """

        if minimum <= 0:
            raise ValueError(
                "Minimum read length must be positive."
            )

        if median < minimum:
            raise ValueError(
                "Read-length median must be >= minimum."
            )

        if maximum < median:
            raise ValueError(
                "Read-length maximum must be >= median."
            )

        if sigma <= 0:
            raise ValueError(
                "Read-length sigma must be positive."
            )

        mu = math.log(median)

        while True:
            sampled = rng.lognormvariate(
                mu,
                sigma,
            )

            length = int(
                round(sampled)
            )

            if minimum <= length <= maximum:
                return length

    # ------------------------------------------------------------------
    # DNA
    # ------------------------------------------------------------------

    @staticmethod
    def _reverse_complement(
        sequence: str,
    ) -> str:
        """Return the reverse complement of a DNA sequence."""

        complement = str.maketrans(
            "ACGTN",
            "TGCAN",
        )

        return sequence.translate(
            complement
        )[::-1]

    @staticmethod
    def _random_substitution(
        base: str,
        rng: random.Random,
    ) -> str:
        """Substitute a nucleotide with one of the other nucleotides."""

        if base not in DNA_BASES:
            return base

        alternatives = [
            candidate
            for candidate in DNA_BASES
            if candidate != base
        ]

        return rng.choice(
            alternatives
        )

    # ------------------------------------------------------------------
    # Fragment generation
    # ------------------------------------------------------------------

    @classmethod
    def _sample_fragment(
        cls,
        sequence: str,
        read_length: int,
        rng: random.Random,
    ) -> tuple[str, int, bool]:
        """Sample one reference fragment.

        Returns:
            fragment:
                Reference sequence used to generate the read.

            start:
                Zero-based coordinate of the fragment on the reference.

            reverse:
                Whether the fragment was reverse-complemented.
        """

        sequence_length = len(sequence)

        if sequence_length < DEFAULT_MIN_READ_LENGTH:
            raise ValueError(
                f"Reference sequence is only {sequence_length} nt long. "
                f"ONT simulation requires references of at least "
                f"{DEFAULT_MIN_READ_LENGTH} nt."
            )

        effective_length = min(
            read_length,
            sequence_length,
        )

        max_start = (
            sequence_length
            - effective_length
        )

        if max_start > 0:
            start = rng.randint(
                0,
                max_start,
            )
        else:
            start = 0

        fragment = sequence[
            start : start + effective_length
        ]

        reverse = (
            rng.random() < 0.5
        )

        if reverse:
            fragment = cls._reverse_complement(
                fragment
            )

        return (
            fragment,
            start,
            reverse,
        )

    # ------------------------------------------------------------------
    # Error model
    # ------------------------------------------------------------------

    @staticmethod
    def _sample_error_type(
        rng: random.Random,
    ) -> str:
        """Sample one ONT error type."""

        insertion_fraction = (
            DEFAULT_INSERTION_FRACTION
        )

        deletion_fraction = (
            DEFAULT_DELETION_FRACTION
        )

        substitution_fraction = (
            DEFAULT_SUBSTITUTION_FRACTION
        )

        total = (
            insertion_fraction
            + deletion_fraction
            + substitution_fraction
        )

        if not math.isclose(
            total,
            1.0,
            rel_tol=1e-9,
        ):
            raise RuntimeError(
                "ONT error fractions must sum to 1.0."
            )

        value = rng.random()

        if value < insertion_fraction:
            return "insertion"

        if value < (
            insertion_fraction
            + deletion_fraction
        ):
            return "deletion"

        return "substitution"

    @staticmethod
    def _quality_for_correct_base(
        error_rate: float,
    ) -> int:
        """Return a Phred score for a correctly sequenced base."""

        # Correct bases are assigned substantially higher quality than
        # error-containing bases.
        probability = max(
            error_rate * 0.25,
            1e-6,
        )

        phred = int(
            round(
                -10.0
                * math.log10(
                    probability
                )
            )
        )

        return min(
            max(
                phred,
                MIN_PHRED,
            ),
            MAX_PHRED,
        )

    @staticmethod
    def _quality_for_error(
        error_rate: float,
    ) -> int:
        """Return a Phred score for an error-containing base."""

        probability = max(
            error_rate,
            1e-6,
        )

        phred = int(
            round(
                -10.0
                * math.log10(
                    probability
                )
            )
        )

        return min(
            max(
                phred,
                MIN_PHRED,
            ),
            MAX_PHRED,
        )

    @classmethod
    def _simulate_read(
        cls,
        reference_read: str,
        rng: random.Random,
        error_rate: float = DEFAULT_ERROR_RATE,
    ) -> tuple[str, str]:
        """Generate one noisy ONT-style read.

        The error model independently evaluates each reference base.

        For a reference base selected as an error:

            insertion    -> inserted base + reference base
            deletion     -> neither base nor quality is emitted
            substitution -> substituted base

        Consequently, the generated sequence and quality string always
        have identical lengths.
        """

        if not (
            0.0
            <= error_rate
            <= 1.0
        ):
            raise ValueError(
                "ONT error_rate must be between 0 and 1."
            )

        sequence: list[str] = []
        qualities: list[str] = []

        correct_phred = (
            cls._quality_for_correct_base(
                error_rate
            )
        )

        error_phred = (
            cls._quality_for_error(
                error_rate
            )
        )

        for base in reference_read:

            # Ambiguous reference bases are retained rather than
            # introducing an artificial nucleotide error.
            if base == "N":
                sequence.append(
                    base
                )

                qualities.append(
                    chr(MIN_PHRED + 33)
                )

                continue

            if rng.random() >= error_rate:
                # Correct base.
                sequence.append(
                    base
                )

                qualities.append(
                    chr(correct_phred + 33)
                )

                continue

            error_type = (
                cls._sample_error_type(
                    rng
                )
            )

            # ------------------------------------------------------
            # Deletion
            # ------------------------------------------------------

            if error_type == "deletion":
                # The reference base does not appear in the output.
                # Therefore neither a nucleotide nor a quality character
                # is emitted.
                continue

            # ------------------------------------------------------
            # Insertion
            # ------------------------------------------------------

            if error_type == "insertion":
                inserted = rng.choice(
                    DNA_BASES
                )

                sequence.append(
                    inserted
                )

                qualities.append(
                    chr(error_phred + 33)
                )

                # Preserve the reference base after the inserted base.
                sequence.append(
                    base
                )

                qualities.append(
                    chr(correct_phred + 33)
                )

                continue

            # ------------------------------------------------------
            # Substitution
            # ------------------------------------------------------

            sequence.append(
                cls._random_substitution(
                    base,
                    rng,
                )
            )

            qualities.append(
                chr(error_phred + 33)
            )

        result_sequence = "".join(
            sequence
        )

        result_quality = "".join(
            qualities
        )

        # Hard invariant for FASTQ validity.
        if len(result_sequence) != len(
            result_quality
        ):
            raise RuntimeError(
                "Internal ONT FASTQ generation error: "
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

        if len(sequence) != len(
            quality
        ):
            raise ValueError(
                "FASTQ sequence/quality length mismatch for "
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
        accession: str,
        number_of_reads: int,
        rng: random.Random,
        r_handle,
        read_id_prefix: str,
    ) -> None:
        """Generate ONT reads from one reference."""

        sequence = self._read_fasta(
            reference_path,
            accession=accession,
        )

        if len(sequence) < (
            DEFAULT_MIN_READ_LENGTH
        ):
            raise ValueError(
                f"Reference {reference_path} is only "
                f"{len(sequence)} nt long, but the minimum "
                f"ONT read length is "
                f"{DEFAULT_MIN_READ_LENGTH} nt."
            )

        for read_index in range(
            number_of_reads
        ):

            requested_length = (
                self._sample_read_length(
                    rng=rng
                )
            )

            # A genome can be shorter than the maximum benchmark
            # read length. In that case the read is simply limited
            # by the available reference sequence.
            effective_length = min(
                requested_length,
                len(sequence),
            )

            (
                fragment,
                start,
                reverse,
            ) = self._sample_fragment(
                sequence=sequence,
                read_length=effective_length,
                rng=rng,
            )

            (
                read_sequence,
                quality,
            ) = self._simulate_read(
                reference_read=fragment,
                rng=rng,
            )

            orientation = (
                "rev"
                if reverse
                else "fwd"
            )

            end = (
                start
                + len(fragment)
            )

            read_id = (
                f"{read_id_prefix}"
                f"_{read_index + 1:08d}"
                f"_start{start}"
                f"_end{end}"
                f"_{orientation}"
            )

            self._write_fastq_record(
                handle=r_handle,
                read_id=read_id,
                sequence=read_sequence,
                quality=quality,
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
        """Generate one native ONT sequencing dataset."""

        if not community.targets:
            raise ValueError(
                "Cannot simulate an empty synthetic community."
            )

        if config.paired_end:
            raise ValueError(
                "ONT simulation does not support paired-end reads. "
                "Set paired_end=false for the ONT platform."
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

        fastq = (
            replicate_dir
            / "reads.fastq"
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

        with fastq.open(
            "w",
            encoding="utf-8",
            newline="\n",
        ) as read_handle:

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
                        accession=reference.accession,
                        number_of_reads=reference_reads,
                        rng=rng,
                        r_handle=read_handle,
                        read_id_prefix=prefix,
                    )

                    total_generated += (
                        reference_reads
                    )

        if total_generated <= 0:
            raise RuntimeError(
                "Native ONT simulation generated no reads. "
                "Check target abundances and read count."
            )

        return Dataset(
            replicate=replicate,
            platform=self.name,
            fastq_r1=fastq,
            fastq_r2=None,
        )


__all__ = [
    "ONTSimulator",
]
