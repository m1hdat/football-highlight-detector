"""Temporal football event detector for SoccerNet PCA-512 features.

The model predicts event timestamps and fine classes directly on the complete
SoccerNet feature timeline.

Checkpoint contract
-------------------
- features: ResNET_TF2_PCA512, 2 FPS, 512 dimensions
- checkpoint weights: checkpoint["ema"]
- classes: Goal, ShotOnTarget, ShotOffTarget, Corner,
  DirectFreeKick, Penalty, Card
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from app.config import (
    DEVICE as DEFAULT_DEVICE,
    FEATURE_DIM,
    FEATURE_FPS,
    FEATURE_TYPE,
    SPOTTER_V2_CHECKPOINT_PATH,
    SPOTTER_V2_MERGE_DISTANCE_SEC,
    SPOTTER_V2_OVERLAP,
    SPOTTER_V2_THRESHOLDS_PATH,
    SPOTTER_V2_WINDOW,
    TOP_K_HIGHLIGHTS,
)
from app.pipeline.feature_utils import load_feature
from app.utils.logger import get_logger

logger = get_logger(__name__)
ProgressCallback = Optional[Callable[[str, int, str], None]]


CLASS_NMS_SECONDS: Dict[str, float] = {
    "Goal": 24.0,
    "ShotOnTarget": 8.0,
    "ShotOffTarget": 8.0,
    "Corner": 14.0,
    "DirectFreeKick": 14.0,
    "Penalty": 25.0,
    "Card": 18.0,
}

# Public/UI labels preserve every fine event class except that both shot
# subtypes are intentionally presented as the single user-facing label ``Shot``.
# The original ShotOnTarget/ShotOffTarget value remains available in ``fine_label``.
DISPLAY_LABEL_MAP: Dict[str, str] = {
    "Goal": "Goal",
    "ShotOnTarget": "Shot",
    "ShotOffTarget": "Shot",
    "Corner": "Corner",
    "DirectFreeKick": "DirectFreeKick",
    "Penalty": "Penalty",
    "Card": "Card",
}

# Clip context is intentionally class-specific. The predicted timestamp is the
# canonical event time; these windows provide enough lead-in and aftermath.
CLIP_CONTEXT_SECONDS: Dict[str, Tuple[float, float]] = {
    "Goal": (15.0, 25.0),
    "Penalty": (15.0, 20.0),
    "ShotOnTarget": (10.0, 12.0),
    "ShotOffTarget": (8.0, 10.0),
    "Corner": (10.0, 12.0),
    "DirectFreeKick": (10.0, 12.0),
    "Card": (8.0, 12.0),
}

# Ranking weights express editorial importance, not model probability.
EVENT_IMPORTANCE: Dict[str, float] = {
    "Goal": 1.00,
    "Penalty": 0.95,
    "ShotOnTarget": 0.90,
    "ShotOffTarget": 0.80,
    "Card": 0.75,
    "Corner": 0.65,
    "DirectFreeKick": 0.60,
}

# Prevent the output reel from collapsing into one visible label. Goals and
# penalties are not practically capped; frequent classes receive Top-K safeguards.
DISPLAY_CLASS_QUOTAS: Dict[str, int] = {
    "Goal": 100,
    "Shot": 6,
    "Corner": 4,
    "DirectFreeKick": 3,
    "Penalty": 100,
    "Card": 2,
}


class TemporalPyramid(nn.Module):
    def __init__(self, d_model: int, dropout: float) -> None:
        super().__init__()
        branch_dim = d_model // 4
        self.branches = nn.ModuleList(
            [
                nn.Sequential(
                    nn.Conv1d(d_model, branch_dim, kernel_size, padding=kernel_size // 2),
                    nn.BatchNorm1d(branch_dim),
                    nn.GELU(),
                )
                for kernel_size in (3, 5, 7, 9)
            ]
        )
        self.out = nn.Sequential(
            nn.Conv1d(branch_dim * 4, d_model, 1),
            nn.BatchNorm1d(d_model),
            nn.GELU(),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.out(torch.cat([branch(x) for branch in self.branches], dim=1))


class ResidualTCNBlock(nn.Module):
    def __init__(self, d_model: int, dilation: int, dropout: float) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(
                d_model,
                d_model,
                kernel_size=3,
                padding=dilation,
                dilation=dilation,
            ),
            nn.BatchNorm1d(d_model),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Conv1d(
                d_model,
                d_model,
                kernel_size=3,
                padding=dilation,
                dilation=dilation,
            ),
            nn.BatchNorm1d(d_model),
            nn.Dropout(dropout),
        )
        self.activation = nn.GELU()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.activation(x + self.net(x))


class SoccerNetSpotter(nn.Module):
    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        hidden: int,
        blocks: int,
        dropout: float,
    ) -> None:
        super().__init__()
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.LayerNorm(hidden),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.pyramid = TemporalPyramid(hidden, dropout)
        self.tcn = nn.Sequential(
            *[
                ResidualTCNBlock(hidden, 2**index, dropout)
                for index in range(blocks)
            ]
        )
        self.event_head = nn.Conv1d(hidden, num_classes, 1)
        self.class_head = nn.Conv1d(hidden, num_classes, 1)
        self.offset_head = nn.Sequential(
            nn.Conv1d(hidden, hidden // 2, 3, padding=1),
            nn.GELU(),
            nn.Conv1d(hidden // 2, 1, 1),
        )

    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        hidden = self.input_proj(x).transpose(1, 2)
        hidden = hidden + self.pyramid(hidden)
        hidden = self.tcn(hidden)
        return {
            "event_logits": self.event_head(hidden).transpose(1, 2),
            "class_logits": self.class_head(hidden).transpose(1, 2),
            "offsets": self.offset_head(hidden).squeeze(1),
        }


@dataclass(frozen=True)
class SpotterBundle:
    model: nn.Module
    class_names: Tuple[str, ...]
    thresholds: Dict[str, float]
    feature_dim: int
    fps: float
    candidate_floor: float
    peak_kernel: int
    max_candidates_per_class: int
    use_amp: bool
    checkpoint_epoch: Optional[int]
    checkpoint_best_map: Optional[float]


def _safe_torch_load(path: str, device: torch.device) -> Dict[str, Any]:
    try:
        checkpoint = torch.load(path, map_location=device, weights_only=False)
    except TypeError:
        checkpoint = torch.load(path, map_location=device)
    if not isinstance(checkpoint, dict):
        raise TypeError("Checkpoint mô hình phải là dictionary")
    return checkpoint


def _load_thresholds(
    path: Optional[str],
    checkpoint: Dict[str, Any],
    class_names: Sequence[str],
) -> Dict[str, float]:
    source: Any = None
    if path and os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as handle:
            source = json.load(handle)
    if source is None:
        source = checkpoint.get("thresholds", {})
    if not isinstance(source, dict):
        raise TypeError("Threshold của mô hình phải là JSON object/dictionary")
    return {name: float(source.get(name, 0.30)) for name in class_names}


def load_spotter_v2(
    checkpoint_path: str = SPOTTER_V2_CHECKPOINT_PATH,
    thresholds_path: str = SPOTTER_V2_THRESHOLDS_PATH,
    device: str = DEFAULT_DEVICE,
) -> SpotterBundle:
    """Load the trained model using EMA weights and validate feature contract."""
    if not os.path.isfile(checkpoint_path):
        raise FileNotFoundError(f"Thiếu checkpoint mô hình: {checkpoint_path}")

    torch_device = torch.device(device)
    checkpoint = _safe_torch_load(checkpoint_path, torch_device)
    cfg = checkpoint.get("cfg", {})
    if not isinstance(cfg, dict):
        raise TypeError("checkpoint['cfg'] phải là dictionary")

    class_to_id = checkpoint.get("class_to_id")
    if not isinstance(class_to_id, dict) or not class_to_id:
        raise ValueError("Checkpoint thiếu class_to_id hợp lệ")
    class_names = tuple(
        name for name, _ in sorted(class_to_id.items(), key=lambda item: int(item[1]))
    )

    feature_dim = int(cfg.get("FEATURE_DIM", FEATURE_DIM))
    fps = float(cfg.get("FPS", FEATURE_FPS))
    if feature_dim != FEATURE_DIM:
        raise ValueError(
            f"Model feature_dim={feature_dim}, backend yêu cầu {FEATURE_DIM}"
        )
    if not math.isclose(fps, float(FEATURE_FPS), rel_tol=0.0, abs_tol=1e-6):
        raise ValueError(f"Model fps={fps}, backend yêu cầu {FEATURE_FPS}")

    model = SoccerNetSpotter(
        input_dim=feature_dim,
        num_classes=len(class_names),
        hidden=int(cfg.get("HIDDEN_DIM", 192)),
        blocks=int(cfg.get("TCN_BLOCKS", 6)),
        dropout=float(cfg.get("DROPOUT", 0.30)),
    ).to(torch_device)

    weights = checkpoint.get("ema")
    if not isinstance(weights, dict):
        raise ValueError("Checkpoint không có EMA weights tại checkpoint['ema']")
    model.load_state_dict(weights, strict=True)
    model.eval()

    thresholds = _load_thresholds(thresholds_path, checkpoint, class_names)
    bundle = SpotterBundle(
        model=model,
        class_names=class_names,
        thresholds=thresholds,
        feature_dim=feature_dim,
        fps=fps,
        candidate_floor=float(cfg.get("AP_CANDIDATE_FLOOR", 0.03)),
        peak_kernel=int(cfg.get("PEAK_KERNEL", 11)),
        max_candidates_per_class=int(cfg.get("MAX_CANDIDATES_PER_CLASS", 120)),
        use_amp=bool(cfg.get("AMP", True)),
        checkpoint_epoch=(
            int(checkpoint["epoch"]) if checkpoint.get("epoch") is not None else None
        ),
        checkpoint_best_map=(
            float(checkpoint["best_map"])
            if checkpoint.get("best_map") is not None
            else None
        ),
    )
    logger.info(
        "[EventDetector] Loaded epoch=%s best_mAP@10s=%s classes=%s thresholds=%s",
        bundle.checkpoint_epoch,
        bundle.checkpoint_best_map,
        list(bundle.class_names),
        bundle.thresholds,
    )
    return bundle


def load_and_normalize_feature(feature_path: str, feature_dim: int) -> np.ndarray:
    """Load one PCA feature timeline and apply per-video standardization."""
    features = load_feature(feature_path)
    features = np.asarray(features, dtype=np.float32)
    if features.ndim != 2:
        raise ValueError(f"Feature phải có 2 chiều, nhận được {features.shape}")
    if features.shape[0] == 0:
        raise ValueError("Feature rỗng")
    if not np.isfinite(features).all():
        raise ValueError("Feature chứa NaN hoặc infinity")

    if features.shape[1] > feature_dim:
        features = features[:, :feature_dim]
    elif features.shape[1] < feature_dim:
        features = np.pad(features, ((0, 0), (0, feature_dim - features.shape[1])))

    mean = features.mean(axis=0, keepdims=True)
    std = features.std(axis=0, keepdims=True)
    features = (features - mean) / (std + 1e-5)
    return np.ascontiguousarray(features, dtype=np.float32)


@torch.inference_mode()
def predict_full_sequence(
    model: nn.Module,
    features: np.ndarray,
    device: torch.device,
    *,
    window: int = SPOTTER_V2_WINDOW,
    overlap: int = SPOTTER_V2_OVERLAP,
    use_amp: bool = True,
    progress_callback: ProgressCallback = None,
) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Sliding inference with overlap-averaged logits over a complete video."""
    if window <= 0:
        raise ValueError("SPOTTER_V2_WINDOW phải dương")
    if overlap < 0 or overlap >= window:
        raise ValueError("SPOTTER_V2_OVERLAP phải thỏa 0 <= overlap < window")

    total_frames = len(features)
    num_classes = model.event_head.out_channels  # type: ignore[attr-defined]
    event_acc = np.zeros((total_frames, num_classes), dtype=np.float32)
    class_acc = np.zeros((total_frames, num_classes), dtype=np.float32)
    offset_acc = np.zeros(total_frames, dtype=np.float32)
    counts = np.zeros(total_frames, dtype=np.float32)

    step = window - overlap
    starts = list(range(0, max(1, total_frames - window + 1), step))
    if not starts or starts[-1] + window < total_frames:
        starts.append(max(0, total_frames - window))

    model.eval()
    for index, start in enumerate(starts, start=1):
        end = min(total_frames, start + window)
        chunk = features[start:end]
        valid = len(chunk)
        if valid < window:
            chunk = np.pad(chunk, ((0, window - valid), (0, 0)))

        inputs = torch.from_numpy(chunk).unsqueeze(0).to(device)
        amp_enabled = use_amp and device.type == "cuda"
        with torch.autocast(
            device_type=device.type,
            dtype=torch.float16,
            enabled=amp_enabled,
        ):
            outputs = model(inputs)

        event_acc[start:end] += outputs["event_logits"][0, :valid].float().cpu().numpy()
        class_acc[start:end] += outputs["class_logits"][0, :valid].float().cpu().numpy()
        offset_acc[start:end] += outputs["offsets"][0, :valid].float().cpu().numpy()
        counts[start:end] += 1.0

        if progress_callback:
            progress = 42 + int(round(18 * index / max(1, len(starts))))
            progress_callback(
                "detecting_highlight",
                progress,
                f"Mô hình đang quét timeline ({index}/{len(starts)})...",
            )

    counts = np.maximum(counts, 1.0)
    return (
        torch.from_numpy(event_acc / counts[:, None]),
        torch.from_numpy(class_acc / counts[:, None]),
        torch.from_numpy(offset_acc / counts),
    )


def temporal_nms(
    predictions: List[Dict[str, Any]],
    class_names: Sequence[str],
) -> List[Dict[str, Any]]:
    kept: List[Dict[str, Any]] = []
    for class_id, class_name in enumerate(class_names):
        radius = CLASS_NMS_SECONDS.get(class_name, 12.0)
        same_class = sorted(
            (p for p in predictions if p["class_id"] == class_id),
            key=lambda item: item["score"],
            reverse=True,
        )
        selected: List[Dict[str, Any]] = []
        for prediction in same_class:
            if all(
                abs(prediction["time_sec"] - other["time_sec"]) > radius
                for other in selected
            ):
                selected.append(prediction)
        kept.extend(selected)
    return sorted(kept, key=lambda item: item["time_sec"])


def decode_sequence(
    event_logits: torch.Tensor,
    class_logits: torch.Tensor,
    offsets: torch.Tensor,
    *,
    class_names: Sequence[str],
    fps: float,
    candidate_floor: float,
    peak_kernel: int,
    max_candidates_per_class: int,
    thresholds: Dict[str, float],
) -> List[Dict[str, Any]]:
    """Decode sparse class-specific event peaks and correct their timestamps."""
    event_probs = torch.sigmoid(event_logits).cpu()
    class_probs = torch.softmax(class_logits, dim=-1).cpu()
    offsets = offsets.cpu()

    pooled = F.max_pool1d(
        event_probs.T.unsqueeze(0),
        kernel_size=peak_kernel,
        stride=1,
        padding=peak_kernel // 2,
    ).squeeze(0).T

    peaks = (event_probs >= pooled - 1e-7) & (event_probs >= candidate_floor)
    raw: List[Dict[str, Any]] = []
    time_indices, class_indices = torch.where(peaks)
    max_frame = max(0, event_probs.shape[0] - 1)

    for time_index, class_id in zip(time_indices.tolist(), class_indices.tolist()):
        event_score = float(event_probs[time_index, class_id])
        class_score = float(class_probs[time_index, class_id])
        score = event_score * (0.65 + 0.35 * class_score)

        corrected_frame = float(time_index) + float(offsets[time_index]) * fps
        corrected_frame = min(max(corrected_frame, 0.0), float(max_frame))
        class_name = class_names[class_id]
        raw.append(
            {
                "frame": round(corrected_frame, 3),
                "time_sec": round(corrected_frame / fps, 3),
                "class_id": int(class_id),
                "fine_label": class_name,
                "display_label": DISPLAY_LABEL_MAP.get(class_name, class_name),
                "score": round(score, 6),
                "event_score": round(event_score, 6),
                "class_score": round(class_score, 6),
            }
        )

    limited: List[Dict[str, Any]] = []
    for class_id in range(len(class_names)):
        candidates = sorted(
            (p for p in raw if p["class_id"] == class_id),
            key=lambda item: item["score"],
            reverse=True,
        )[:max_candidates_per_class]
        limited.extend(candidates)

    after_nms = temporal_nms(limited, class_names)
    predictions = [
        prediction
        for prediction in after_nms
        if prediction["score"]
        >= float(thresholds.get(prediction["fine_label"], 0.30))
    ]
    return sorted(predictions, key=lambda item: item["time_sec"])


def _threshold_relative_score(
    prediction: Dict[str, Any], thresholds: Dict[str, float]
) -> float:
    label = str(prediction["fine_label"])
    threshold = max(float(thresholds.get(label, 0.30)), 1e-6)
    ratio = min(float(prediction["score"]) / threshold, 3.0)
    return ratio * EVENT_IMPORTANCE.get(label, 0.50)


def cluster_events(
    predictions: Sequence[Dict[str, Any]],
    *,
    thresholds: Dict[str, float],
    video_duration: float,
    merge_distance_sec: float = SPOTTER_V2_MERGE_DISTANCE_SEC,
) -> List[Dict[str, Any]]:
    """Merge nearby fine events into one coherent clip candidate.

    This keeps event metadata (e.g. Corner -> ShotOffTarget) while preventing
    duplicate clips for the same play.
    """
    if not predictions:
        return []

    groups: List[List[Dict[str, Any]]] = []
    for prediction in sorted(predictions, key=lambda item: item["time_sec"]):
        if not groups:
            groups.append([dict(prediction)])
            continue
        previous_time = float(groups[-1][-1]["time_sec"])
        if float(prediction["time_sec"]) - previous_time <= merge_distance_sec:
            groups[-1].append(dict(prediction))
        else:
            groups.append([dict(prediction)])

    candidates: List[Dict[str, Any]] = []
    for group in groups:
        for event in group:
            event["selection_score"] = _threshold_relative_score(event, thresholds)
        main_event = max(
            group,
            key=lambda event: (float(event["selection_score"]), float(event["score"])),
        )

        starts: List[float] = []
        ends: List[float] = []
        for event in group:
            before, after = CLIP_CONTEXT_SECONDS.get(event["fine_label"], (10.0, 12.0))
            starts.append(max(0.0, float(event["time_sec"]) - before))
            ends.append(min(video_duration, float(event["time_sec"]) + after))

        fine_events: List[str] = []
        for event in sorted(group, key=lambda item: item["time_sec"]):
            label = str(event["fine_label"])
            if label not in fine_events:
                fine_events.append(label)

        candidates.append(
            {
                "start": round(min(starts), 2),
                "end": round(max(ends), 2),
                "peak_second": round(float(main_event["time_sec"]), 3),
                "label": str(main_event["display_label"]),
                "fine_label": str(main_event["fine_label"]),
                "fine_events": fine_events,
                "highlight_confidence": round(float(main_event["score"]), 6),
                "label_confidence": round(float(main_event["class_score"]), 6),
                "event_score": round(float(main_event["event_score"]), 6),
                "selection_score": round(float(main_event["selection_score"]), 6),
                "events": [
                    {
                        "time_sec": float(event["time_sec"]),
                        "fine_label": str(event["fine_label"]),
                        "display_label": str(event["display_label"]),
                        "score": float(event["score"]),
                        "event_score": float(event["event_score"]),
                        "class_score": float(event["class_score"]),
                    }
                    for event in sorted(group, key=lambda item: item["time_sec"])
                ],
            }
        )
    return candidates


def select_highlight_candidates(
    candidates: Sequence[Dict[str, Any]],
    top_k: int = TOP_K_HIGHLIGHTS,
) -> List[Dict[str, Any]]:
    """Select a balanced Top-K reel with display-class quotas."""
    if top_k <= 0 or not candidates:
        return []

    ranked = sorted(
        (dict(candidate) for candidate in candidates),
        key=lambda item: (
            -float(item.get("selection_score", 0.0)),
            -float(item.get("highlight_confidence", 0.0)),
            float(item.get("peak_second", 0.0)),
        ),
    )

    selected: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {key: 0 for key in DISPLAY_CLASS_QUOTAS}

    # Goals are mandatory editorial events.
    for candidate in ranked:
        if candidate.get("label") == "Goal":
            selected.append(candidate)
            counts["Goal"] = counts.get("Goal", 0) + 1

    for candidate in ranked:
        if candidate in selected:
            continue
        if len(selected) >= max(top_k, counts.get("Goal", 0)):
            break
        display_label = str(candidate.get("label", "Unknown"))
        quota = DISPLAY_CLASS_QUOTAS.get(display_label, top_k)
        if counts.get(display_label, 0) >= quota:
            continue
        selected.append(candidate)
        counts[display_label] = counts.get(display_label, 0) + 1

    return sorted(selected, key=lambda item: float(item["peak_second"]))


def spot_events_from_feature(
    feature_path: str,
    bundle: SpotterBundle,
    *,
    device: str = DEFAULT_DEVICE,
    window: int = SPOTTER_V2_WINDOW,
    overlap: int = SPOTTER_V2_OVERLAP,
    progress_callback: ProgressCallback = None,
) -> List[Dict[str, Any]]:
    features = load_and_normalize_feature(feature_path, bundle.feature_dim)
    torch_device = torch.device(device)
    event_logits, class_logits, offsets = predict_full_sequence(
        bundle.model,
        features,
        torch_device,
        window=window,
        overlap=overlap,
        use_amp=bundle.use_amp,
        progress_callback=progress_callback,
    )
    predictions = decode_sequence(
        event_logits,
        class_logits,
        offsets,
        class_names=bundle.class_names,
        fps=bundle.fps,
        candidate_floor=bundle.candidate_floor,
        peak_kernel=bundle.peak_kernel,
        max_candidates_per_class=bundle.max_candidates_per_class,
        thresholds=bundle.thresholds,
    )
    logger.info(
        "[EventDetector] Decoded %d events from %s (duration %.1fs)",
        len(predictions),
        feature_path,
        len(features) / bundle.fps,
    )
    return predictions


def run_spotter_v2(
    feature_path: str,
    video_duration: float,
    bundle: SpotterBundle,
    *,
    device: str = DEFAULT_DEVICE,
    top_k: int = TOP_K_HIGHLIGHTS,
    progress_callback: ProgressCallback = None,
) -> List[Dict[str, Any]]:
    """End-to-end feature -> sparse events -> merged balanced highlight clips."""
    predictions = spot_events_from_feature(
        feature_path,
        bundle,
        device=device,
        progress_callback=progress_callback,
    )
    merged = cluster_events(
        predictions,
        thresholds=bundle.thresholds,
        video_duration=video_duration,
    )
    selected = select_highlight_candidates(merged, top_k=top_k)
    logger.info(
        "[EventDetector] %d raw events -> %d merged plays -> %d selected highlights",
        len(predictions),
        len(merged),
        len(selected),
    )
    return selected
