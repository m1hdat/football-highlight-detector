"""Feature loading helpers for the event detection pipeline."""

import numpy as np

from app.config import FEATURE_DIM


def load_feature(feature_path: str) -> np.ndarray:
    """Load and validate a float32 feature timeline shaped ``[T, 512]``."""
    features = np.load(feature_path).astype(np.float32)
    if features.ndim != 2 or features.shape[1] != FEATURE_DIM:
        raise ValueError(
            f"Feature shape không hợp lệ: {features.shape}; "
            f"expected [T, {FEATURE_DIM}]"
        )
    if features.shape[0] == 0:
        raise ValueError("Feature timeline is empty")
    if not np.isfinite(features).all():
        raise ValueError("Feature timeline contains NaN or infinity")
    return features
