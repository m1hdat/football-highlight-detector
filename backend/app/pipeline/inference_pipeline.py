"""End-to-end football highlight detection pipeline."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from app.config import (
    DEVICE,
    FEATURE_DIM,
    FEATURE_FPS,
    SPOTTER_V2_CHECKPOINT_PATH,
    SPOTTER_V2_THRESHOLDS_PATH,
    TOP_K_HIGHLIGHTS,
)
from app.pipeline.feature_extractor import extract_feature
from app.pipeline.spotter_v2 import load_spotter_v2, run_spotter_v2
from app.services.ffmpeg_service import get_video_duration
from app.services.storage_service import get_feature_path
from app.utils.logger import get_logger

logger = get_logger(__name__)
ProgressCallback = Optional[Callable[[str, int, str], None]]

_spotter_v2_cache = None


def _report(callback: ProgressCallback, status: str, progress: int, message: str) -> None:
    if callback:
        callback(status, progress, message)


def _get_spotter_v2():
    global _spotter_v2_cache
    if _spotter_v2_cache is None:
        _spotter_v2_cache = load_spotter_v2(
            checkpoint_path=SPOTTER_V2_CHECKPOINT_PATH,
            thresholds_path=SPOTTER_V2_THRESHOLDS_PATH,
            device=DEVICE,
        )
    return _spotter_v2_cache


def run_full_pipeline(
    video_path: str,
    job_id: str,
    progress_callback: ProgressCallback = None,
) -> List[Dict]:
    """Run feature extraction, event detection and highlight selection."""
    feature_path = get_feature_path(job_id)

    _report(progress_callback, "extracting_feature", 10, "Đang trích xuất SoccerNet feature...")
    extract_feature(
        video_path,
        feature_path,
        fps=FEATURE_FPS,
        feature_dim=FEATURE_DIM,
    )

    _report(
        progress_callback,
        "detecting_highlight",
        40,
        "Mô hình đang phát hiện thời điểm và loại sự kiện...",
    )
    bundle = _get_spotter_v2()
    video_duration = get_video_duration(video_path)
    results = run_spotter_v2(
        feature_path=feature_path,
        video_duration=video_duration,
        bundle=bundle,
        device=DEVICE,
        top_k=TOP_K_HIGHLIGHTS,
        progress_callback=progress_callback,
    )

    _report(
        progress_callback,
        "classifying",
        72,
        "Đã gộp sự kiện gần nhau và chọn các highlight quan trọng...",
    )
    if not results:
        logger.info("Không tìm thấy sự kiện vượt ngưỡng dự đoán")

    for index, result in enumerate(results, start=1):
        result["id"] = index
        safe_label = str(result.get("label", "unknown")).lower().replace(" ", "-")
        result["clip_id"] = f"{job_id}_{safe_label}_{index:02d}"
    return results
