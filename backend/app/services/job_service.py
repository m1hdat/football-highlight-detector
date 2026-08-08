"""Quản lý trạng thái job trong RAM (MVP một process)."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Dict

from app.schemas import JOB_STATUSES

_JOBS: Dict[str, dict] = {}
_LOCK = Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_job(job_id: str, video_path: str) -> None:
    with _LOCK:
        _JOBS[job_id] = {
            "job_id": job_id,
            "video_path": video_path,
            "status": "uploaded",
            "progress": 0,
            "message": "Video đã upload, chờ xử lý.",
            "created_at": _now(),
            "updated_at": _now(),
        }


def update_job_status(job_id: str, status: str, progress: int, message: str) -> None:
    if status not in JOB_STATUSES:
        raise ValueError(f"Invalid status: {status}. Phải thuộc {JOB_STATUSES}")
    progress = max(0, min(100, int(progress)))
    with _LOCK:
        job = _JOBS.setdefault(job_id, {"job_id": job_id, "created_at": _now()})
        job.update(
            {
                "status": status,
                "progress": progress,
                "message": message,
                "updated_at": _now(),
            }
        )


def get_job_status(job_id: str) -> dict:
    with _LOCK:
        if job_id not in _JOBS:
            raise KeyError(f"job_id không tồn tại: {job_id}")
        return dict(_JOBS[job_id])


def mark_job_failed(job_id: str, error_message: str) -> None:
    update_job_status(job_id, "failed", 0, f"Xử lý thất bại: {error_message}")


def mark_job_done(job_id: str) -> None:
    update_job_status(job_id, "done", 100, "Xử lý hoàn tất.")


def delete_job(job_id: str) -> None:
    with _LOCK:
        _JOBS.pop(job_id, None)
