from __future__ import annotations

import os

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from app.config import (
    ALLOWED_VIDEO_EXTENSIONS,
    CLEANUP_INPUTS_AFTER_SUCCESS,
    KEEP_FAILED_INPUTS,
    MAX_UPLOAD_SIZE_BYTES,
    MAX_UPLOAD_SIZE_MB,
    MAX_VIDEO_DURATION_SEC,
    MIN_VIDEO_DURATION_SEC,
    SPOTTER_V2_CHECKPOINT_PATH,
    SPOTTER_V2_THRESHOLDS_PATH,
    UPLOAD_CHUNK_SIZE_BYTES,
)
from app.pipeline.feature_extractor import preflight_soccernet_extractor
from app.pipeline.inference_pipeline import run_full_pipeline
from app.schemas import UploadResponse
from app.services import job_service, storage_service
from app.services.cleanup_service import cleanup_stale_artifacts
from app.services.ffmpeg_service import cut_highlight_clips, get_video_duration
from app.utils.file_utils import get_extension
from app.utils.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


def _preflight_pipeline() -> None:
    preflight_soccernet_extractor()
    missing = [
        path
        for path in (SPOTTER_V2_CHECKPOINT_PATH, SPOTTER_V2_THRESHOLDS_PATH)
        if not os.path.isfile(path)
    ]
    if missing:
        raise FileNotFoundError("Thiếu artifact mô hình nhận diện sự kiện: " + ", ".join(missing))


def _process_video_job(job_id: str, video_path: str) -> None:
    """Run the highlight detection pipeline and update job progress."""

    def report(status: str, progress: int, message: str) -> None:
        job_service.update_job_status(job_id, status, progress, message)

    success = False
    try:
        results = run_full_pipeline(video_path, job_id, progress_callback=report)

        report("cutting_video", 82, "Đang cắt các clip highlight bằng FFmpeg...")
        output_dir = storage_service.get_output_dir(job_id)
        results = cut_highlight_clips(video_path, results, output_dir)
        storage_service.save_result_json(job_id, results)

        success = True
        job_service.mark_job_done(job_id)
    except Exception as exc:
        logger.exception("[job %s] Pipeline thất bại", job_id)
        job_service.mark_job_failed(job_id, str(exc))
    finally:
        if success and CLEANUP_INPUTS_AFTER_SUCCESS:
            storage_service.cleanup_input_artifacts(job_id)
        elif not success and not KEEP_FAILED_INPUTS:
            storage_service.cleanup_input_artifacts(job_id)


@router.post("/upload", response_model=UploadResponse, status_code=202)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> UploadResponse:
    """Upload one video and create a background highlight-processing job."""
    try:
        _preflight_pipeline()
    except (FileNotFoundError, RuntimeError, TimeoutError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    filename = file.filename or "video.mp4"
    extension = get_extension(filename)
    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_VIDEO_EXTENSIONS))
        raise HTTPException(
            status_code=415,
            detail=f"Định dạng không hỗ trợ. Cho phép: {allowed}",
        )

    cleanup_stale_artifacts()
    job_id = storage_service.generate_job_id()

    try:
        video_path, _ = await storage_service.save_upload_file_stream(
            file=file,
            filename=filename,
            job_id=job_id,
            max_bytes=MAX_UPLOAD_SIZE_BYTES,
            chunk_size=UPLOAD_CHUNK_SIZE_BYTES,
        )
    except storage_service.UploadTooLargeError as exc:
        raise HTTPException(
            status_code=413,
            detail=f"Video vượt quá giới hạn {MAX_UPLOAD_SIZE_MB} MB",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        duration = get_video_duration(video_path)
        if duration < MIN_VIDEO_DURATION_SEC:
            raise ValueError(f"Video phải dài ít nhất {MIN_VIDEO_DURATION_SEC:g} giây")
        if duration > MAX_VIDEO_DURATION_SEC:
            raise ValueError(
                f"Video dài tối đa {MAX_VIDEO_DURATION_SEC / 3600:g} giờ trong phiên bản hiện tại"
            )
    except Exception as exc:
        storage_service.cleanup_input_artifacts(job_id)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job_service.create_job(job_id, video_path)
    background_tasks.add_task(_process_video_job, job_id, video_path)
    return UploadResponse(
        job_id=job_id,
        filename=os.path.basename(video_path),
        status="uploaded",
    )
