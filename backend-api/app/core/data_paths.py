from pathlib import Path

from app.core.config import settings


def get_innovalab_data_dir() -> Path:
    configured = settings.INNOVALAB_DATA_DIR
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).resolve().parents[4] / "data"
