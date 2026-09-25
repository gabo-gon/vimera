from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Platform(str, Enum):
    """Supported sequencing platforms."""

    ILLUMINA = "illumina"
    ONT = "ont"


class GenomeSelection(str, Enum):
    """Strategies for selecting representative genomes."""

    REFERENCE = "reference"
    RANDOM = "random"
    DIVERSE = "diverse"
    ALL_COMPLETE = "all_complete"


class ReferenceSource(str, Enum):
    """Source used to resolve viral reference genomes."""

    AUTO = "auto"
    LOCAL = "local"
    NCBI = "ncbi"


class ReferenceConfig(BaseModel):
    """Configuration for viral reference-genome resolution."""

    model_config = ConfigDict(extra="forbid")

    source: ReferenceSource = ReferenceSource.AUTO

    cache_dir: Path = Path("~/.vimera/references")

    refresh: bool = False

    max_genomes: int = Field(
        default=10,
        ge=1,
    )

    batch_size: int = Field(
        default=100,
        ge=1,
    )

    @field_validator("cache_dir")
    @classmethod
    def expand_cache_dir(cls, value: Path) -> Path:
        return value.expanduser()


class Target(BaseModel):
    """A viral taxonomic target included in a synthetic community."""

    model_config = ConfigDict(extra="forbid")

    taxid: int = Field(gt=0)

    abundance: float = Field(
        gt=0,
        le=1,
    )

    genome_selection: GenomeSelection = GenomeSelection.REFERENCE

    @field_validator("taxid")
    @classmethod
    def validate_taxid(cls, value: int) -> int:
        if value <= 0:
            raise ValueError(
                "TaxID must be a positive integer."
            )

        return value


class Background(BaseModel):
    """Background components of a synthetic metagenomic community."""

    model_config = ConfigDict(extra="forbid")

    host_taxids: list[int] = Field(
        default_factory=list
    )

    bacterial_taxids: list[int] = Field(
        default_factory=list
    )

    viral_taxids: list[int] = Field(
        default_factory=list
    )

    near_neighbor_taxids: list[int] = Field(
        default_factory=list
    )

    abundance: float = Field(
        default=0.0,
        ge=0,
        le=1,
    )



class SequencingConfig(BaseModel):
    """Sequencing and dataset-generation parameters."""

    model_config = ConfigDict(extra="forbid")

    platform: Platform = Platform.ILLUMINA

    reads: int = Field(
        default=100_000,
        gt=0,
    )

    replicates: int = Field(
        default=1,
        gt=0,
    )

    seed: int | None = Field(
        default=None,
        ge=0,
    )

    read_length: int | None = Field(
        default=None,
        gt=0,
    )

    paired_end: bool = True

    error_rate: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )

    fragment_mean: int = Field(
        default=200,
        gt=0,
    )

    fragment_sd: int = Field(
        default=10,
        gt=0,
    )
    


class SimulationConfig(BaseModel):
    """Complete configuration for a synthetic virome experiment."""

    model_config = ConfigDict(extra="forbid")

    targets: list[Target] = Field(
        min_length=1
    )

    background: Background = Field(
        default_factory=Background
    )

    sequencing: SequencingConfig = Field(
        default_factory=SequencingConfig
    )

    reference: ReferenceConfig = Field(
        default_factory=ReferenceConfig
    )

    output_dir: Path = Path(
        "results/synthetic"
    )

    experiment_name: str = "experiment_001"

    @field_validator("targets")
    @classmethod
    def validate_targets(
        cls,
        targets: list[Target],
    ) -> list[Target]:

        taxids = [
            target.taxid
            for target in targets
        ]

        if len(taxids) != len(set(taxids)):
            raise ValueError(
                "Duplicate TaxIDs are not allowed in targets."
            )

        return targets


class NullConfig(BaseModel):
    """Configuration for empirical target-absent null generation."""

    model_config = ConfigDict(extra="forbid")

    input_fastq: Path

    read_group: Path

    replicates: int = Field(
        default=1000,
        gt=0,
    )

    seed: int | None = Field(
        default=None,
        ge=0,
    )

    output_dir: Path = Path(
        "results/empirical"
    )


class SpikeInConfig(BaseModel):
    """Configuration for empirical spike-in experiments."""

    model_config = ConfigDict(extra="forbid")

    input_fastq: Path

    target_taxids: list[int] = Field(
        min_length=1
    )

    abundances: list[float] = Field(
        min_length=1
    )

    replicates: int = Field(
        default=10,
        gt=0,
    )

    seed: int | None = Field(
        default=None,
        ge=0,
    )

    output_dir: Path = Path(
        "results/empirical"
    )

    @field_validator("target_taxids")
    @classmethod
    def validate_taxids(
        cls,
        taxids: list[int],
    ) -> list[int]:

        if any(
            taxid <= 0
            for taxid in taxids
        ):
            raise ValueError(
                "All TaxIDs must be positive integers."
            )

        if len(taxids) != len(set(taxids)):
            raise ValueError(
                "Duplicate TaxIDs are not allowed."
            )

        return taxids

    @field_validator("abundances")
    @classmethod
    def validate_abundances(
        cls,
        abundances: list[float],
    ) -> list[float]:

        if any(
            abundance <= 0 or abundance > 1
            for abundance in abundances
        ):
            raise ValueError(
                "Abundances must be greater than 0 and at most 1."
            )

        return abundances


ConfigModel = (
    SimulationConfig
    | NullConfig
    | SpikeInConfig
)


def model_to_dict(
    model: BaseModel,
) -> dict[str, Any]:
    """Return a JSON/YAML-serializable representation."""

    return model.model_dump(
        mode="json"
    )