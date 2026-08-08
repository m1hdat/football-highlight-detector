from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.services import storage_service
from app.services.ffmpeg_service import create_zip_from_clips
from app.utils.file_utils import validate_clip_id, validate_job_id

router = APIRouter()


@router.get("/clips/{clip_id}")
def get_clip(clip_id: str, download: bool = Query(default=False)):
    """Phát inline cho preview; thêm ?download=true để tải file."""
    try:
        validate_clip_id(clip_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="clip_id không hợp lệ") from exc

    job_id = clip_id.split("_", 1)[0]
    clip_path = os.path.join(storage_service.get_output_dir(job_id, create=False), f"{clip_id}.mp4")
    if not os.path.isfile(clip_path):
        raise HTTPException(status_code=404, detail="Clip không tồn tại")

    disposition = "attachment" if download else "inline"
    return FileResponse(
        clip_path,
        media_type="video/mp4",
        headers={"Content-Disposition": f'{disposition}; filename="{clip_id}.mp4"'},
    )


@router.get("/jobs/{job_id}/download-all")
def download_all_clips(job_id: str):
    try:
        validate_job_id(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="job_id không hợp lệ") from exc

    results = storage_service.load_result_json(job_id)
    if not results:
        raise HTTPException(status_code=404, detail="Job chưa có kết quả")

    output_dir = storage_service.get_output_dir(job_id, create=False)
    clip_paths = []
    for result in results:
        clip_id = result.get("clip_id")
        if clip_id:
            path = os.path.join(output_dir, f"{clip_id}.mp4")
            if os.path.isfile(path):
                clip_paths.append(path)
    if not clip_paths:
        raise HTTPException(status_code=404, detail="Không tìm thấy clip để tải")

    zip_path = os.path.join(output_dir, f"{job_id}_highlights.zip")
    create_zip_from_clips(clip_paths, zip_path)
    return FileResponse(zip_path, media_type="application/zip", filename=f"{job_id}_highlights.zip")
