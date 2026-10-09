"""Fixtures compartidos de los tests de datos."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

RUTA_DATASET = RAIZ / "data" / "processed" / "habilitaciones_caba_clean.csv"


@pytest.fixture(scope="session")
def df() -> pd.DataFrame:
    """Dataset procesado, cargado una sola vez para toda la sesión."""
    if not RUTA_DATASET.exists():
        pytest.skip(
            "No existe data/processed/habilitaciones_caba_clean.csv; "
            "ejecutar primero notebook/01_exploracion_y_limpieza.ipynb"
        )
    return pd.read_csv(RUTA_DATASET, encoding="utf-8-sig", low_memory=False)
