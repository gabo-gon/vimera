from pathlib import Path

DEFAULTS = {
    "simulation": {
        "experiment_name": "experiment_001",
        "output_dir": Path("results/synthetic"),
        "sequencing": {
            "platform": "illumina",
            "reads": 100_000,
            "replicates": 1,
            "seed": None,
            "read_length": None,
            "paired_end": True,
            "error_rate": None,
        },
        "reference": {
            "source": "auto",
            "cache_dir": Path.home() / ".vimera" / "references",
            "refresh": False,
        },
        "background": {
            "host_taxids": [],
            "bacterial_taxids": [],
            "viral_taxids": [],
            "near_neighbor_taxids": [],
            "abundance": 0.0,
        },
    },
    "null": {
        "replicates": 1_000,
        "seed": None,
        "output_dir": Path("results/empirical"),
    },
    "spikein": {
        "replicates": 10,
        "seed": None,
        "output_dir": Path("results/empirical"),
    },
}

DEFAULT_NULL_CONFIG = DEFAULTS["null"]
DEFAULT_SPIKEIN_CONFIG = DEFAULTS["spikein"]
DEFAULT_SIMULATION_CONFIG = DEFAULTS["simulation"]