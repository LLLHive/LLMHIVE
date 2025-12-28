import os
from pathlib import Path

import pandas as pd
import pytest


def _find_modeldb_excel() -> Path:
    """
    Resolve the canonical ModelDB Excel file for tests.

    Priority:
      1) env MODELDB_TEST_EXCEL (or MODELDB_EXCEL_PATH / MODELDB_EXCEL)
      2) newest LLMHive_OpenRouter_SingleSheet_ModelDB_Enriched_*.xlsx in data/modeldb/
    """
    env_path = (
        os.getenv("MODELDB_TEST_EXCEL")
        or os.getenv("MODELDB_EXCEL_PATH")
        or os.getenv("MODELDB_EXCEL")
    )
    if env_path:
        p = Path(env_path).expanduser().resolve()
        if p.exists():
            return p
        raise FileNotFoundError(f"MODELDB_TEST_EXCEL points to missing file: {p}")

    modeldb_dir = Path(__file__).resolve().parent.parent  # .../data/modeldb
    candidates = sorted(
        modeldb_dir.glob("LLMHive_OpenRouter_SingleSheet_ModelDB_Enriched_*.xlsx"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(
            f"No canonical ModelDB Excel found in {modeldb_dir}. "
            "Expected a file like LLMHive_OpenRouter_SingleSheet_ModelDB_Enriched_*.xlsx "
            "or set MODELDB_TEST_EXCEL."
        )
    return candidates[0]


@pytest.fixture(scope="session")
def excel_path() -> Path:
    """Path to the canonical ModelDB Excel used by tests."""
    return _find_modeldb_excel()


@pytest.fixture(scope="session")
def df(excel_path: Path) -> pd.DataFrame:
    """Load ModelDB Excel into a DataFrame for safety tests."""
    return pd.read_excel(excel_path)
