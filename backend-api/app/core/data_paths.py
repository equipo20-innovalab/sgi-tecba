import os
from pathlib import Path


def get_innovalab_data_dir() -> Path:
    configured = os.getenv("INNOVALAB_DATA_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).resolve().parents[4] / "data"
