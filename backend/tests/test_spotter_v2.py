from app.pipeline.spotter_v2 import (
    DISPLAY_LABEL_MAP,
    cluster_events,
    select_highlight_candidates,
)


def _event(time_sec, fine_label, display_label, score, class_score=0.9, event_score=None):
    return {
        "time_sec": float(time_sec),
        "fine_label": fine_label,
        "display_label": display_label,
        "score": float(score),
        "event_score": float(event_score if event_score is not None else score),
        "class_score": float(class_score),
        "class_id": 0,
    }


def test_cluster_merges_corner_and_shot_into_one_play():
    thresholds = {"Corner": 0.4, "ShotOffTarget": 0.08}
    predictions = [
        _event(100.0, "Corner", "Corner", 0.75),
        _event(103.0, "ShotOffTarget", "Shot", 0.24),
    ]
    result = cluster_events(
        predictions,
        thresholds=thresholds,
        video_duration=200.0,
        merge_distance_sec=5.0,
    )
    assert len(result) == 1
    assert result[0]["fine_events"] == ["Corner", "ShotOffTarget"]
    assert result[0]["label"] == "Shot"
    assert result[0]["start"] == 90.0
    assert result[0]["end"] == 113.0


def test_balanced_selector_respects_corner_quota():
    candidates = []
    for index in range(8):
        candidates.append(
            {
                "peak_second": float(index * 20),
                "label": "Corner",
                "selection_score": 10.0 - index,
                "highlight_confidence": 0.9,
            }
        )
    for index in range(6):
        candidates.append(
            {
                "peak_second": float(200 + index * 20),
                "label": "Shot",
                "selection_score": 5.0 - index * 0.1,
                "highlight_confidence": 0.5,
            }
        )
    selected = select_highlight_candidates(candidates, top_k=10)
    assert len(selected) == 10
    assert sum(item["label"] == "Corner" for item in selected) <= 4
    assert sum(item["label"] == "Shot" for item in selected) >= 6


def test_visible_label_mapping_only_merges_shot_subtypes():
    assert DISPLAY_LABEL_MAP["ShotOnTarget"] == "Shot"
    assert DISPLAY_LABEL_MAP["ShotOffTarget"] == "Shot"
    assert DISPLAY_LABEL_MAP["Corner"] == "Corner"
    assert DISPLAY_LABEL_MAP["DirectFreeKick"] == "DirectFreeKick"
    assert DISPLAY_LABEL_MAP["Penalty"] == "Penalty"
    assert "SetPiece" not in DISPLAY_LABEL_MAP.values()
