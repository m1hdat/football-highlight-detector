from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

_JOB_ID_RE = re.compile(r"^[a-f0-9]{12}$")
_CLIP_ID_RE = re.compile(r"^[a-f0-9]{12}_[a-z0-9-]+_[0-9]{2,3}$")


def safe_makedirs(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def remove_if_exists(path: str) -> None:
    if os.path.isdir(path):
        shutil.rmtree(path, ignore_errors=True)
    elif os.path.exists(path):
        os.remove(path)


def get_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def sanitize_filename(filename: str) -> str:
    """Loại path traversal và ký tự không an toàn khỏi tên file upload."""
    base = Path(filename or "video.mp4").name
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(base).stem).strip("._") or "video"
    suffix = Path(base).suffix.lower()
    return f"{stem}{suffix}"


def validate_job_id(job_id: str) -> str:
    if not _JOB_ID_RE.fullmatch(job_id):
        raise ValueError("job_id không hợp lệ")
    return job_id


def validate_clip_id(clip_id: str) -> str:
    if not _CLIP_ID_RE.fullmatch(clip_id):
        raise ValueError("clip_id không hợp lệ")
    return clip_id
