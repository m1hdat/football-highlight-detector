"""Tiện ích ffprobe/FFmpeg cho video input và clip output."""

from __future__ import annotations

import json
import math
import os
import subprocess
import zipfile
from typing import Dict, List

from app.config import FFMPEG_TIMEOUT_SEC, FFPROBE_TIMEOUT_SEC
from app.utils.file_utils import validate_clip_id
from app.utils.logger import get_logger

logger = get_logger(__name__)


class VideoProcessingError(RuntimeError):
    pass


def _run_command(cmd: List[str], timeout: int) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise VideoProcessingError(f"Không tìm thấy lệnh {cmd[0]} trong PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise VideoProcessingError(f"{cmd[0]} chạy quá thời gian cho phép") from exc
    except subprocess.CalledProcessError as exc:
        print('STDERR: ' , exc.stderr)
        stderr = (exc.stderr or "").strip()[-2000:]
        raise VideoProcessingError(f"{cmd[0]} thất bại: {stderr}") from exc


def get_video_duration(video_path: str) -> float:
    if not os.path.isfile(video_path):
        raise VideoProcessingError("Video không tồn tại")
    result = _run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            video_path,
        ],
        timeout=FFPROBE_TIMEOUT_SEC,
    )
    try:
        duration = float(json.loads(result.stdout)["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise VideoProcessingError("Không đọc được thời lượng video") from exc
    if not math.isfinite(duration) or duration <= 0:
        raise VideoProcessingError("Thời lượng video không hợp lệ")
    return duration


def cut_video_clip(video_path: str, start: float, end: float, output_path: str) -> str:
    if start < 0 or end <= start:
        raise ValueError(f"Khoảng cắt không hợp lệ: {start}-{end}")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    duration = end - start
    cmd = [
        "ffmpeg",
        "-nostdin",
        "-y",
        "-ss",
        f"{start:.3f}",
        "-i",
        video_path,
        "-t",
        f"{duration:.3f}",
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-sn",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        "-avoid_negative_ts",
        "make_zero",
        output_path,
    ]
    try:
        _run_command(cmd, timeout=FFMPEG_TIMEOUT_SEC)
        if not os.path.isfile(output_path) or os.path.getsize(output_path) < 1024:
            raise VideoProcessingError("FFmpeg tạo clip rỗng hoặc không hợp lệ")
    except Exception:
        if os.path.exists(output_path):
            os.remove(output_path)
        raise
    logger.info("[ffmpeg] Cut %.1fs-%.1fs -> %s", start, end, output_path)
    return output_path


def cut_highlight_clips(video_path: str, results: List[Dict], output_dir: str) -> List[Dict]:
    """Clamp timestamp theo video thật và bỏ các candidate hoàn toàn ngoài video."""
    os.makedirs(output_dir, exist_ok=True)
    video_duration = get_video_duration(video_path)
    updated: List[Dict] = []

    for result in results:
        start = max(0.0, float(result["start"]))
        end = min(float(result["end"]), video_duration)
        if start >= video_duration or end - start < 0.25:
            logger.warning("Bỏ candidate ngoài video: %.2f-%.2f / %.2f", start, end, video_duration)
            continue

        clip_id = result.get("clip_id") or f"clip_{int(result.get('id', 0)):02d}"
        validate_clip_id(clip_id)
        clip_path = os.path.join(output_dir, f"{clip_id}.mp4")
        try:
            cut_video_clip(video_path, start, end, clip_path)
        except Exception as exc:
            logger.exception("Không cắt được clip %s: %s", clip_id, exc)
            continue

        updated.append(
            {
                **result,
                "start": round(start, 2),
                "end": round(end, 2),
                "clip_path": clip_path,
                "clip_url": f"/clips/{clip_id}",
            }
        )

    if results and not updated:
        raise VideoProcessingError("Không tạo được clip hợp lệ nào từ kết quả model")
    return updated


def create_zip_from_clips(clip_paths: List[str], zip_path: str) -> str:
    """Video đã nén sẵn; ZIP_STORED nhanh hơn và không tốn CPU nén lại."""
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)
    temp_path = f"{zip_path}.tmp"
    with zipfile.ZipFile(temp_path, "w", compression=zipfile.ZIP_STORED) as archive:
        for path in clip_paths:
            if os.path.isfile(path):
                archive.write(path, arcname=os.path.basename(path))
    os.replace(temp_path, zip_path)
    return zip_path
