from typing import List

from fastapi import APIRouter, HTTPException, Response, status

from app.schemas import HighlightResult, JobStatus
from app.services import job_service, storage_service
from app.utils.file_utils import validate_job_id

router = APIRouter()


def _valid_job_or_404(job_id: str) -> str:
    try:
        return validate_job_id(job_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="job_id không hợp lệ") from exc


@router.get("/jobs/{job_id}/status", response_model=JobStatus)
def get_job_status(job_id: str) -> JobStatus:
    _valid_job_or_404(job_id)
    try:
        current = job_service.get_job_status(job_id)
    except KeyError as exc:
        # Sau khi restart, RAM mất trạng thái nhưng kết quả trên disk có thể còn.
        if storage_service.has_result_json(job_id):
            return JobStatus(
                job_id=job_id,
                status="done",
                progress=100,
                message="Đã tìm thấy kết quả lưu trên máy chủ.",
            )
        raise HTTPException(status_code=404, detail="job_id không tồn tại") from exc
    return JobStatus(**current)


@router.get("/jobs/{job_id}/results", response_model=List[HighlightResult])
def get_job_results(job_id: str) -> List[HighlightResult]:
    _valid_job_or_404(job_id)
    if not storage_service.has_result_json(job_id):
        raise HTTPException(status_code=404, detail="Chưa có kết quả hoặc job_id không tồn tại")
    results = storage_service.load_result_json(job_id)
    return [HighlightResult(**result) for result in results]


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: str) -> Response:
    """Cho phép người dùng chủ động xóa video/feature/clip của một job."""
    _valid_job_or_404(job_id)
    storage_service.cleanup_all_job_artifacts(job_id)
    job_service.delete_job(job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
