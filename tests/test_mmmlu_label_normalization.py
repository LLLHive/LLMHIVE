import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_ROOT / "scripts"))

from run_category_benchmarks import _normalize_mmmlu_correct_answer


def test_normalizes_known_bad_virology_row_label() -> None:
    normalized = _normalize_mmmlu_correct_answer(
        "Versi klasifikasi yang diperbarui menunjukkan bahwa famili parvovirus memiliki berapa genus?",
        [
            "Memiliki 5 genus",
            "Jumlah tipe virus yang sangat banyak",
            "Hanya satu virus",
            "Hanya tiga virus",
        ],
        "B",
        "virology",
    )
    assert normalized == "A"


def test_leaves_other_mmmlu_rows_unchanged() -> None:
    normalized = _normalize_mmmlu_correct_answer(
        "I critici della teoria del comando divino hanno affermato che la teoria implica che i comandi di Dio siano _____.",
        ["ben sostenuti", "non chiari", "imperscrutabili", "arbitrari"],
        "D",
        "philosophy",
    )
    assert normalized == "D"
