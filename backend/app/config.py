"""Central configuration for the football highlight backend."""

from __future__ import annotations

import os
from typing import List


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")
FEATURE_DIR = os.path.join(BASE_DIR, "data", "features")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "outputs")
TEMP_DIR = os.path.join(BASE_DIR, "data", "temp")
MODEL_ARTIFACT_DIR = os.path.join(BASE_DIR, "model_artifacts")

SPOTTER_V2_DIR = os.path.join(MODEL_ARTIFACT_DIR, "spotter_v2")
SPOTTER_V2_CHECKPOINT_PATH = os.path.join(SPOTTER_V2_DIR, "best_model.pt")
SPOTTER_V2_THRESHOLDS_PATH = os.path.join(SPOTTER_V2_DIR, "best_thresholds.json")

# Feature contract used by the current event detection model.
FEATURE_FPS = 2
FEATURE_DIM = 512
FEATURE_TYPE = "ResNET_TF2_PCA512"

# Official SoccerNet TF2 extractor, kept in a separate Conda environment.
THIRD_PARTY_DIR = os.path.join(BASE_DIR, "third_party")
SOCCERNET_FEATURE_DIR = os.environ.get(
    "SOCCERNET_FEATURE_DIR",
    os.path.join(THIRD_PARTY_DIR, "soccernet_features"),
)
SOCCERNET_EXTRACTOR_SCRIPT = os.path.join(
    SOCCERNET_FEATURE_DIR, "VideoFeatureExtractor.py"
)
SOCCERNET_RUNNER_PATH = os.path.join(
    BASE_DIR, "scripts", "soccernet_chunked_runner.py"
)
SOCCERNET_PCA_PATH = os.path.join(SOCCERNET_FEATURE_DIR, "pca_512_TF2.pkl")
SOCCERNET_AVERAGE_PATH = os.path.join(
    SOCCERNET_FEATURE_DIR, "average_512_TF2.pkl"
)

# Default execution uses ``conda run`` so Conda also supplies the environment's
# DLL/OpenSSL paths. A direct Python executable remains available as an explicit
# compatibility override for advanced users.
SOCCERNET_EXECUTION_MODE = os.environ.get(
    "SOCCERNET_EXECUTION_MODE", "conda"
).strip().lower()
SOCCERNET_CONDA_ENV = os.environ.get(
    "SOCCERNET_CONDA_ENV", "SoccerNet-FeatureExtraction"
)
SOCCERNET_CONDA_EXE = os.environ.get(
    "SOCCERNET_CONDA_EXE", os.environ.get("CONDA_EXE", "conda")
)
SOCCERNET_EXTRACTOR_PYTHON = os.environ.get(
    "SOCCERNET_EXTRACTOR_PYTHON", ""
).strip()
SOCCERNET_GPU = int(os.environ.get("SOCCERNET_GPU", "-1"))
SOCCERNET_TRANSFORM = os.environ.get("SOCCERNET_TRANSFORM", "crop")
SOCCERNET_GRABBER = os.environ.get("SOCCERNET_GRABBER", "opencv")
SOCCERNET_EXTRACT_TIMEOUT_SEC = int(
    os.environ.get("SOCCERNET_EXTRACT_TIMEOUT_SEC", str(6 * 60 * 60))
)
SOCCERNET_PREFLIGHT_TIMEOUT_SEC = int(
    os.environ.get("SOCCERNET_PREFLIGHT_TIMEOUT_SEC", "120")
)
SOCCERNET_CHUNK_DURATION_SEC = float(
    os.environ.get("SOCCERNET_CHUNK_DURATION_SEC", "300")
)

# Temporal event detection settings.
SPOTTER_V2_WINDOW = int(os.environ.get("SPOTTER_V2_WINDOW", "1024"))
SPOTTER_V2_OVERLAP = int(os.environ.get("SPOTTER_V2_OVERLAP", "256"))
SPOTTER_V2_MERGE_DISTANCE_SEC = float(
    os.environ.get("SPOTTER_V2_MERGE_DISTANCE_SEC", "5")
)
TOP_K_HIGHLIGHTS = int(os.environ.get("TOP_K_HIGHLIGHTS", "10"))

# Upload validation.
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"}
MAX_UPLOAD_SIZE_MB = int(os.environ.get("MAX_UPLOAD_SIZE_MB", "2048"))
MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024
UPLOAD_CHUNK_SIZE_MB = int(os.environ.get("UPLOAD_CHUNK_SIZE_MB", "8"))
UPLOAD_CHUNK_SIZE_BYTES = UPLOAD_CHUNK_SIZE_MB * 1024 * 1024
MIN_VIDEO_DURATION_SEC = float(os.environ.get("MIN_VIDEO_DURATION_SEC", "2"))
MAX_VIDEO_DURATION_SEC = float(
    os.environ.get("MAX_VIDEO_DURATION_SEC", str(3 * 60 * 60))
)

# Cleanup policy.
CLEANUP_INPUTS_AFTER_SUCCESS = (
    os.environ.get("CLEANUP_INPUTS_AFTER_SUCCESS", "true").lower() == "true"
)
KEEP_FAILED_INPUTS = os.environ.get("KEEP_FAILED_INPUTS", "true").lower() == "true"
STALE_INPUT_TTL_HOURS = float(os.environ.get("STALE_INPUT_TTL_HOURS", "24"))
OUTPUT_TTL_HOURS = float(os.environ.get("OUTPUT_TTL_HOURS", "24"))
CLEANUP_ON_STARTUP = (
    os.environ.get("CLEANUP_ON_STARTUP", "true").lower() == "true"
)

# Runtime.
DEVICE = os.environ.get("INFERENCE_DEVICE", "cpu")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))
RELOAD = os.environ.get("RELOAD", "true").lower() == "true"
FFMPEG_TIMEOUT_SEC = int(os.environ.get("FFMPEG_TIMEOUT_SEC", "1800"))
FFPROBE_TIMEOUT_SEC = int(os.environ.get("FFPROBE_TIMEOUT_SEC", "30"))


def _parse_origins(raw: str) -> List[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


CORS_ORIGINS = _parse_origins(
    os.environ.get(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    )
)


def ensure_directories() -> None:
    """Create runtime directories when they do not exist."""
    for directory in (
        UPLOAD_DIR,
        FEATURE_DIR,
        OUTPUT_DIR,
        TEMP_DIR,
        MODEL_ARTIFACT_DIR,
        SPOTTER_V2_DIR,
        SOCCERNET_FEATURE_DIR,
    ):
        os.makedirs(directory, exist_ok=True)
