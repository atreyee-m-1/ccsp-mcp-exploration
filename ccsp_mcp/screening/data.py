"""Data loading for the CCSP dose-response screening domain."""

import os
from pathlib import Path

import pandas as pd

# Configuration
DATA_DIR = os.environ.get(
    "CCSP_DATA_DIR",
    str(Path(__file__).parent.parent.parent / "sample_data"),
)
# When set, load a single real-data file (CSV/TSV) instead of the
# multi-file synthetic sample_data/ directory. Takes priority over DATA_DIR.
DATA_FILE = os.environ.get("CCSP_DATA_FILE")

_data_cache: dict[str, pd.DataFrame] = {}


def _load_real_data_file(path: Path) -> pd.DataFrame:
    """Load a single real-data CSV/TSV and normalize it to the schema the tools expect."""
    sep = "\t" if path.suffix.lower() == ".tsv" else ","
    df = pd.read_csv(path, sep=sep)

    if "Compound name" in df.columns:
        df = df.rename(columns={"cmpd": "compound_code", "Compound name": "compound"})

    return df


def load_data() -> pd.DataFrame:
    """Load and cache the dose-response data."""
    if "dose_response" not in _data_cache:
        if DATA_FILE:
            path = Path(DATA_FILE)
            if not path.exists():
                raise FileNotFoundError(f"Data file not found: {path}")
            _data_cache["dose_response"] = _load_real_data_file(path)
        else:
            path = Path(DATA_DIR) / "dose_response_parameters.csv"
            if not path.exists():
                raise FileNotFoundError(f"Data file not found: {path}")
            _data_cache["dose_response"] = pd.read_csv(path)
    return _data_cache["dose_response"]


def has_lineage() -> bool:
    """Whether the loaded dataset has cancer-lineage annotations."""
    return "lineage" in load_data().columns


def load_cell_line_metadata() -> pd.DataFrame:
    """Load cell line metadata."""
    if "cell_lines" not in _data_cache:
        path = Path(DATA_DIR) / "cell_line_metadata.csv"
        if path.exists():
            _data_cache["cell_lines"] = pd.read_csv(path)
        else:
            _data_cache["cell_lines"] = pd.DataFrame()
    return _data_cache["cell_lines"]


def load_compound_metadata() -> pd.DataFrame:
    """Load compound metadata."""
    if "compounds" not in _data_cache:
        path = Path(DATA_DIR) / "compound_metadata.csv"
        if path.exists():
            _data_cache["compounds"] = pd.read_csv(path)
        else:
            _data_cache["compounds"] = pd.DataFrame()
    return _data_cache["compounds"]
