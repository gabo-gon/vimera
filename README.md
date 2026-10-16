**VIMERA** -Viral Metagenomic Evaluation & Reliability Assessment- is an open-source framework for reproducible viral metagenomics benchmarking and empirical viral detection assessment.

The project is designed around two complementary questions:

> **Can my analysis pipeline detect what I know is there?**

and

> **How confident should I be that a viral signal detected in a real sample is actually there?**

Vimera combines controlled synthetic dataset generation with empirical evaluation of viral read groups detected in real sequencing data.

---

## Project goals

Vimera has two main modules.

### 1. Controlled Synthetic Virome Benchmarking

Generate reproducible synthetic metagenomic datasets containing one or multiple known viral targets at controlled abundances.

The user can define:

* one or multiple viral targets
* NCBI TaxIDs or taxonomic names
* target abundances
* host background
* bacterial background
* other viral background
* taxonomic near-neighbors
* sequencing platform
* dataset size
* number of replicates
* genome-selection strategy
* sequencing quality/error conditions
* simulating sequences for viral discovery

Vimera retrieves appropriate reference genomes and uses sequencing simulators.

Every generated dataset will retain detailed ground truth and provenance.

---

### 2. Empirical Viral Detection Assessment

Evaluate viral signals obtained from real sequencing datasets.

The input can be the output of essentially any read-classification or detection method, including:

* Kraken2
* Kaiju
* BLAST
* read mapping
* assembly
* custom classifiers
* other detection pipelines

Vimera standardizes detected read groups and evaluates them using empirical null distributions and controlled spike-ins.

The module provides:

* target-absent null distributions
* matched random resampling
* taxonomic near-neighbor/decoy challenges
* controlled spike-in experiments
* detection curves
* empirical detection limits
* empirical tail probabilities
* confidence estimates
* classifier comparison

The objective is to distinguish:

**"I found these reads"**

from:

**"These reads represent evidence that this virus is actually present."**

---

## Architecture

Vimera is designed as three complementary layers:

```text
┌──────────────────────────────────────────────┐
│                    Vimera                    │
├──────────────────────────────────────────────┤
│                                              │
│  Python scientific engine                    │
│  ───────────────────────                     │
│  Taxonomy • genomes • simulation • nulls     │
│  spike-ins • statistics • provenance         │
│                                              │
├──────────────────────────────────────────────┤
│                                              │
│  Snakemake workflow layer                    │
│  ─────────────────────────                   │
│  Reproducible multi-step execution           │
│                                              │
├──────────────────────────────────────────────┤
│                                              │
│  R analysis/reporting                        │
│  ────────────────────                        │
│  Visualization • statistical summaries       │
│  publication-ready reports                   │
│                                              │
└──────────────────────────────────────────────┘
```

The scientific logic resides in the Python package.

Snakemake is used for workflow orchestration rather than containing scientific logic.

R is an optional analysis and reporting layer.

---

## Project structure

```text
vimera/
│
├── README.md
├── LICENSE
├── CITATION.cff
├── pyproject.toml
├── environment.yml
├── .gitignore
├── .editorconfig
│
├── configs/
│   ├── synthetic/
│   │   ├── minimal.yml
│   │   ├── illumina.yml
│   │   ├── ont.yml
│   │   └── multi_target.yml
│   │
│   └── empirical/
│       ├── null.yml
│       ├── spikein.yml
│       └── complete.yml
│
├── src/
│   └── vimera/
│       ├── __init__.py
│       ├── __main__.py
│       │
│       ├── cli/
│       ├── config/
│       ├── core/
│       ├── ncbi/
│       ├── synthetic/
│       ├── empirical/
│       ├── evaluation/
│       └── reporting/
│
├── workflows/
│   ├── synthetic/
│   └── empirical/
│
├── envs/
│   ├── core.yml
│   ├── ncbi.yml
│   ├── illumina.yml
│   ├── ont.yml
│   └── analysis.yml
│
├── tests/
│
├── R/
│   ├── plots/
│   └── reports/
│
├── docs/
│
└── results/
    └── .gitkeep
```

---

## Configuration

Vimera supports both configuration files and direct command-line execution.

### YAML

```yaml
targets:
  - taxid: 12637
    abundance: 0.001

  - taxid: 12638
    abundance: 0.0005

  - taxid: 12639
    abundance: 0.0001

platform: illumina
reads: 100000
replicates: 10
```

Run with:

```bash
vimera simulate --config config.yml
```

### Command line

Multiple targets can be supplied as comma-separated values:

```bash
vimera simulate \
    --targets 12637,12638,12639 \
    --abundance 0.001,0.0005,0.0001 \
    --platform illumina \
    --reads 100000 \
    --replicates 10
```

```bash
vimera simulate \
    --targets 12637,12638,12639 \
    --target_fasta local_sequences.fasta \
    --abundance 0.001,0.0005,0.0001 \
    --platform illumina \
    --reads 100000 \
    --replicates 10
```

The configuration system follows:

```text
CLI arguments > YAML configuration > software defaults
```

Regardless of how the experiment is launched, Vimera resolves everything into the same internal configuration model.

The resolved configuration is saved with the results to ensure reproducibility.

---

## Reproducibility

Each experiment is intended to retain enough information to reconstruct how the dataset or analysis was generated.

Synthetic datasets will include information such as:

* configuration
* TaxIDs
* selected accessions
* genome-selection strategy
* abundance
* simulator
* simulator parameters
* random seeds
* sequencing platform
* replicate information
* read-level provenance

A typical synthetic experiment will eventually look like:

```text
results/synthetic/experiment_001/
├── config.yml
├── experiment_manifest.json
│
├── dataset_001/
│   ├── reads_R1.fastq.gz
│   ├── reads_R2.fastq.gz
│   ├── truth.tsv
│   ├── abundance.tsv
│   ├── manifest.json
│   └── genomes/
│
└── dataset_002/
    └── ...
```

---

## Development status

Vimera is currently under active development.

The initial development roadmap is:

```text
v0.1  Configuration + CLI foundation [done]
v0.2  NCBI genome retrieval and selection [done]
v0.3  Illumina simulation [done]
v0.4  ONT simulation [done]
v0.5  Rich background/community generation [done]
v0.6  Empirical null distributions
v0.7  Controlled spike-ins
v0.8  Near-neighbor challenges [done]
v0.9  Automated benchmark matrices
v1.0  Stable release + documentation + benchmark datasets
```

The exact versioning and feature boundaries may change during development.

---

## Design principles

Vimera follows several principles:

1. **Reproducibility first**
   Experiments should retain their configuration, provenance, inputs, and random seeds.

2. **Use established simulators**
   Vimera orchestrates existing sequencing simulators rather than reinventing sequencing-error models.

3. **Taxonomy-aware benchmarking**
   Viral targets should be evaluated in biologically relevant taxonomic contexts, including near-neighbor viruses.

4. **Classifier independence**
   Empirical evaluation should not depend on a particular classifier.

5. **Multiple targets are first-class objects**
   A synthetic community may contain one or many viral targets.

6. **Python for scientific logic**
   Scientific operations belong in the Python package, not in Snakefiles.

7. **Snakemake for orchestration**
   Snakemake manages complex workflows, dependencies, resources, and reruns.

8. **R for analysis and reporting**
   R provides an optional layer for statistical visualization and publication-ready reports.

9. **Configuration and CLI are equivalent interfaces**
   YAML and command-line execution should produce the same underlying experiment configuration.

## Installation
🚧 VIMERA is currently under active development. The current release
focuses on synthetic viral metagenome simulation and ground-truth
generation. Downstream benchmark evaluation components are not yet
fully implemented.

### Windows
Clone the repository:
```powershell
git clone <REPOSITORY-URL>
cd vimera
````
Run the installation script:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\INSTALL.ps1
```

Activate the environment:
```powershell
.\.venv\Scripts\Activate.ps1
```

Verify the installation:
```powershell
python -c "import vimera; print('VIMERA OK')"
```

### Linux / macOS
Clone the repository:

```bash
git clone <REPOSITORY-URL>
cd vimera
```

Run:
```bash
chmod +x install.sh
./install.sh
```

Activate the environment:
```bash
source .venv/bin/activate
```

Verify:
```bash
python -c "import vimera; print('VIMERA OK')"
```

### Conda
A Conda environment specification is also provided:
```bash
conda env create -f environment.yml
conda activate vimera
```

The Conda environment is optional; the platform-specific installation
scripts use standard Python virtual environments.
```
```

---

## License

Vimera is released under the terms specified in `LICENSE`.

---

## Citation

If you use VIMERA in your research, please cite and credit the project
and its authors.

### Manuscript in preparation

Gonzalez, G. (2026). VIMERA: A reproducible framework for synthetic
virome benchmarking and empirical assessment of viral detection.
Manuscript in preparation.