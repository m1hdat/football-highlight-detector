from __future__ import annotations

import os
import time
from typing import Dict

from app.config import (
    FEATURE_DIR,
    OUTPUT_DIR,
    OUTPUT_TTL_HOURS,
    STALE_INPUT_TTL_HOURS,
    UPLOAD_DIR,
)
from app.utils.file_utils import remove_if_exists
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _cleanup_children(base_dir: str, ttl_hours: float) -> int:
    if ttl_hours <= 0 or not os.path.isdir(base_dir):
        return 0
    cutoff = time.time() - ttl_hours * 3600
    removed = 0
    for name in os.listdir(base_dir):
        if name.startswith("."):
            continue
        path = os.path.join(base_dir, name)
        try:
            if os.path.getmtime(path) < cutoff:
                remove_if_exists(path)
                removed += 1
        except FileNotFoundError:
            continue
        except OSError as exc:
            logger.warning("Không thể cleanup %s: %s", path, exc)
    return removed


def cleanup_stale_artifacts() -> Dict[str, int]:
    """Xóa input/feature lỗi bị bỏ quên và output quá TTL."""
    result = {
        "uploads": _cleanup_children(UPLOAD_DIR, STALE_INPUT_TTL_HOURS),
        "features": _cleanup_children(FEATURE_DIR, STALE_INPUT_TTL_HOURS),
        "outputs": _cleanup_children(OUTPUT_DIR, OUTPUT_TTL_HOURS),
    }
    logger.info("Cleanup completed: %s", result)
    return result
