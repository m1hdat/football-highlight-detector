"""Shared API schemas."""

from typing import List, Optional

from pydantic import BaseModel


class UploadResponse(BaseModel):
    job_id: str
    filename: str
    status: str


class HighlightCandidate(BaseModel):
    start: float
    end: float
    peak_second: float
    highlight_confidence: float


class LabelPrediction(BaseModel):
    label: str
    label_confidence: float


class HighlightResult(BaseModel):
    """Final highlight clip returned to the frontend."""

    clip_id: str
    start: float
    end: float
    peak_second: float
    label: str
    highlight_confidence: float
    label_confidence: float
    clip_url: str

    # Optional fine-grained model diagnostics.
    fine_label: Optional[str] = None
    fine_events: Optional[List[str]] = None
    event_score: Optional[float] = None
    selection_score: Optional[float] = None


class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: int
    message: str


JOB_STATUSES = (
    "uploaded",
    "extracting_feature",
    "detecting_highlight",
    "classifying",
    "cutting_video",
    "done",
    "failed",
)
