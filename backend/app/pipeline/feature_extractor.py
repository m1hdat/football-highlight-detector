"""Official SoccerNet TF2 feature extraction wrapper.

The backend extracts ``ResNET_TF2_PCA512`` features at 2 FPS for the event
spotting pipeline. By default the legacy TensorFlow extractor is launched with
``conda run`` so Conda configures its OpenSSL and DLL paths correctly.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import List, Sequence, Tuple

import numpy as np

from app.config import (
    FEATURE_DIM,
    FEATURE_FPS,
    SOCCERNET_AVERAGE_PATH,
    SOCCERNET_CHUNK_DURATION_SEC,
    SOCCERNET_CONDA_ENV,
    SOCCERNET_CONDA_EXE,
    SOCCERNET_EXECUTION_MODE,
    SOCCERNET_EXTRACTOR_PYTHON,
    SOCCERNET_EXTRACTOR_SCRIPT,
    SOCCERNET_EXTRACT_TIMEOUT_SEC,
    SOCCERNET_GPU,
    SOCCERNET_GRABBER,
    SOCCERNET_PCA_PATH,
    SOCCERNET_PREFLIGHT_TIMEOUT_SEC,
    SOCCERNET_RUNNER_PATH,
    SOCCERNET_TRANSFORM,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

_REQUIRED_ASSETS = (
    SOCCERNET_EXTRACTOR_SCRIPT,
    SOCCERNET_PCA_PATH,
    SOCCERNET_RUNNER_PATH,
    SOCCERNET_AVERAGE_PATH,
)

_RUNTIME_IMPORT_CHECK = (
    "import ssl; "
    "import tensorflow as tf; "
    "import SoccerNet; "
    "import cv2; "
    "import skvideo; "
    "import imutils; "
    "import sklearn; "
    "print('python-runtime-ok'); "
    "print('tensorflow=' + tf.__version__); "
    "print('openssl=' + ssl.OPENSSL_VERSION)"
)


def extract_feature(
    video_path: str,
    output_path: str,
    fps: int = FEATURE_FPS,
    feature_dim: int = FEATURE_DIM,
) -> str:
    """Extract an official SoccerNet feature timeline shaped ``[T, 512]``."""
    if fps <= 0:
        raise ValueError("fps must be greater than 0")
    if feature_dim != FEATURE_DIM:
        raise ValueError(f"Mô hình hiện tại yêu cầu feature_dim={FEATURE_DIM}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    return run_soccernet_extractor(video_path, output_path, fps=fps)


def check_soccernet_assets() -> List[str]:
    """Return missing official SoccerNet extractor assets."""
    return [str(path) for path in _REQUIRED_ASSETS if not os.path.isfile(path)]


def _resolve_executable(value: str, label: str) -> str:
    expanded = os.path.expandvars(os.path.expanduser(value))
    if os.path.isfile(expanded):
        return os.path.abspath(expanded)
    resolved = shutil.which(expanded)
    if resolved:
        return resolved
    raise FileNotFoundError(f"{label} was not found: {value!r}")


def _build_runtime_prefix() -> Tuple[str, ...]:
    """Return the command prefix used to execute the legacy extractor.

    The default mode is ``conda``. Direct interpreter execution is only used
    when ``SOCCERNET_EXECUTION_MODE=python`` is set explicitly.
    """
    if SOCCERNET_EXECUTION_MODE == "python":
        if not SOCCERNET_EXTRACTOR_PYTHON:
            raise ValueError(
                "SOCCERNET_EXECUTION_MODE=python requires "
                "SOCCERNET_EXTRACTOR_PYTHON."
            )
        python_executable = _resolve_executable(
            SOCCERNET_EXTRACTOR_PYTHON,
            "SoccerNet extractor Python",
        )
        return (python_executable,)

    if SOCCERNET_EXECUTION_MODE != "conda":
        raise ValueError(
            "SOCCERNET_EXECUTION_MODE must be either 'conda' or 'python'."
        )

    conda_executable = _resolve_executable(SOCCERNET_CONDA_EXE, "Conda executable")
    return (
        conda_executable,
        "run",
        "--no-capture-output",
        "-n",
        SOCCERNET_CONDA_ENV,
        "python",
    )


def _child_environment() -> dict:
    """Create a clean child environment without leaking backend Python paths."""
    environment = os.environ.copy()
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    environment["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    environment["CUDA_VISIBLE_DEVICES"] = str(SOCCERNET_GPU)
    return environment


@lru_cache(maxsize=1)
def _probe_soccernet_runtime(prefix: Tuple[str, ...]) -> str:
    command = [*prefix, "-c", _RUNTIME_IMPORT_CHECK]
    try:
        completed = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=SOCCERNET_PREFLIGHT_TIMEOUT_SEC,
            check=False,
            env=_child_environment(),
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(
            "SoccerNet runtime preflight timed out. Run setup.ps1 again or "
            "check the Conda environment manually."
        ) from exc

    output = (completed.stdout or "").strip()
    if completed.returncode != 0:
        raise RuntimeError(
            "SoccerNet runtime is not ready. The configured environment must "
            "import TensorFlow, SoccerNet, OpenCV, scikit-video, imutils and "
            "scikit-learn.\n" + output
        )
    return output


def preflight_soccernet_extractor() -> dict:
    """Validate assets and the dedicated runtime before accepting an upload."""
    missing = check_soccernet_assets()
    if missing:
        raise FileNotFoundError(
            "Missing official SoccerNet extractor assets: "
            + ", ".join(missing)
            + ". Run .\\setup.ps1 from the repository root."
        )

    prefix = _build_runtime_prefix()
    runtime_output = _probe_soccernet_runtime(prefix)
    mode = "python" if len(prefix) == 1 else "conda"
    return {
        "ready": True,
        "execution_mode": mode,
        "runtime_command": list(prefix),
        "conda_environment": SOCCERNET_CONDA_ENV if mode == "conda" else None,
        "runtime": runtime_output.splitlines(),
        "script": str(SOCCERNET_EXTRACTOR_SCRIPT),
        "feature_type": "ResNET_TF2_PCA512",
        "fps": FEATURE_FPS,
        "dim": FEATURE_DIM,
    }


def build_soccernet_command(
    video_path: str,
    output_path: str,
    fps: int = FEATURE_FPS,
    video_duration: float | None = None,
) -> List[str]:
    """Build the memory-bounded command around the official extractor."""
    missing = check_soccernet_assets()
    if missing:
        raise FileNotFoundError(
            "Missing official SoccerNet extractor assets:\n- "
            + "\n- ".join(missing)
            + "\nRun .\\setup.ps1 from the repository root."
        )

    if video_duration is None:
        from app.services.ffmpeg_service import get_video_duration

        video_duration = get_video_duration(video_path)

    return [
        *_build_runtime_prefix(),
        str(SOCCERNET_RUNNER_PATH),
        "--path_video",
        os.path.abspath(video_path),
        "--path_features",
        os.path.abspath(output_path),
        "--video_duration",
        str(float(video_duration)),
        "--chunk_duration",
        str(float(SOCCERNET_CHUNK_DURATION_SEC)),
        "--fps",
        str(float(fps)),
        "--gpu",
        str(SOCCERNET_GPU),
        "--transform",
        SOCCERNET_TRANSFORM,
        "--grabber",
        SOCCERNET_GRABBER,
        "--extractor_dir",
        str(Path(SOCCERNET_EXTRACTOR_SCRIPT).parent),
        "--pca",
        str(SOCCERNET_PCA_PATH),
        "--pca_scaler",
        str(SOCCERNET_AVERAGE_PATH),
    ]


def run_soccernet_extractor(
    video_path: str,
    output_path: str,
    fps: int = FEATURE_FPS,
) -> str:
    """Run SoccerNet's official TF2 ResNet-152 + PCA512 extractor."""
    command = build_soccernet_command(video_path, output_path, fps=fps)
    logger.info("[feature] starting official SoccerNet extractor")
    logger.debug("Extractor command: %s", command)

    try:
        completed = subprocess.run(
            command,
            cwd=str(Path(SOCCERNET_EXTRACTOR_SCRIPT).parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=SOCCERNET_EXTRACT_TIMEOUT_SEC,
            check=False,
            env=_child_environment(),
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(
            f"SoccerNet feature extraction exceeded {SOCCERNET_EXTRACT_TIMEOUT_SEC}s"
        ) from exc

    if completed.stdout:
        for line in completed.stdout.splitlines():
            logger.info("[SoccerNet] %s", line)

    if completed.returncode != 0:
        raise RuntimeError(
            "Official SoccerNet extractor failed with exit code "
            f"{completed.returncode}. Review the [SoccerNet] lines immediately "
            "above this error."
        )

    validate_feature_file(output_path, expected_dim=FEATURE_DIM)

    features = np.load(output_path)
    if features.dtype != np.float32:
        np.save(output_path, features.astype(np.float32))
        features = np.load(output_path, mmap_mode="r")

    _warn_if_rate_is_unexpected(video_path, feature_count=features.shape[0], fps=fps)
    logger.info(
        "[feature] saved shape=%s dtype=%s -> %s",
        features.shape,
        features.dtype,
        output_path,
    )
    return output_path


def _validate_feature_array(features: np.ndarray, feature_dim: int = FEATURE_DIM) -> None:
    if features.ndim != 2:
        raise ValueError(f"Feature array must be 2D [T, D], got {features.shape}")
    if features.shape[0] <= 0:
        raise ValueError("Feature array is empty")
    if features.shape[1] != feature_dim:
        raise ValueError(
            f"Feature dimension must be {feature_dim}, got {features.shape[1]}"
        )
    if not np.isfinite(features).all():
        raise ValueError("Feature array contains NaN or infinity")


def validate_feature_file(path: str, expected_dim: int = FEATURE_DIM) -> str:
    """Validate extractor output before model inference."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"SoccerNet extractor did not create: {path}")
    features = np.load(path, mmap_mode="r")
    _validate_feature_array(features, feature_dim=expected_dim)
    return path


def _warn_if_rate_is_unexpected(video_path: str, feature_count: int, fps: int) -> None:
    try:
        from app.services.ffmpeg_service import get_video_duration

        duration = get_video_duration(video_path)
    except Exception:
        return
    expected = max(1.0, duration * fps)
    relative_error = abs(feature_count - expected) / expected
    if relative_error > 0.10:
        logger.warning(
            "Feature count differs from expected rate: count=%s expected≈%.1f (%sfps)",
            feature_count,
            expected,
            fps,
        )
