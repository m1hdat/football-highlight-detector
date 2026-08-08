"""Chạy cleanup thủ công: python scripts/cleanup_data.py"""

from app.config import ensure_directories
from app.services.cleanup_service import cleanup_stale_artifacts


if __name__ == "__main__":
    ensure_directories()
    print(cleanup_stale_artifacts())
