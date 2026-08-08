from pathlib import Path

import numpy as np
import pytest

from app.pipeline import feature_extractor as fe


def test_validate_feature_file_accepts_contract(tmp_path: Path):
    path = tmp_path / "features.npy"
    np.save(path, np.zeros((20, 512), dtype=np.float32))
    assert fe.validate_feature_file(str(path)) == str(path)


def test_validate_feature_file_rejects_wrong_dim(tmp_path: Path):
    path = tmp_path / "features.npy"
    np.save(path, np.zeros((20, 2048), dtype=np.float32))
    with pytest.raises(ValueError, match="dimension"):
        fe.validate_feature_file(str(path))


def _mock_assets(monkeypatch, tmp_path: Path):
    script = tmp_path / "VideoFeatureExtractor.py"
    pca = tmp_path / "pca_512_TF2.pkl"
    average = tmp_path / "average_512_TF2.pkl"
    runner = tmp_path / "soccernet_chunked_runner.py"
    for path in (script, pca, average, runner):
        path.write_bytes(b"x")

    monkeypatch.setattr(fe, "SOCCERNET_EXTRACTOR_SCRIPT", str(script))
    monkeypatch.setattr(fe, "SOCCERNET_PCA_PATH", str(pca))
    monkeypatch.setattr(fe, "SOCCERNET_AVERAGE_PATH", str(average))
    monkeypatch.setattr(fe, "SOCCERNET_RUNNER_PATH", str(runner))
    monkeypatch.setattr(fe, "_REQUIRED_ASSETS", (str(script), str(pca), str(average), str(runner)))
    return script, pca, average, runner


def test_build_soccernet_command_with_direct_python(monkeypatch, tmp_path: Path):
    _, pca, average, _ = _mock_assets(monkeypatch, tmp_path)
    python = tmp_path / "python.exe"
    python.write_bytes(b"x")

    monkeypatch.setattr(fe, "SOCCERNET_EXECUTION_MODE", "python")
    monkeypatch.setattr(fe, "SOCCERNET_EXTRACTOR_PYTHON", str(python))

    command = fe.build_soccernet_command(
        "input.mp4", "features.npy", fps=2, video_duration=10
    )
    assert command[0] == str(python)
    assert "--pca" in command
    assert str(pca) in command
    assert "--pca_scaler" in command
    assert str(average) in command
    assert "--chunk_duration" in command
    assert "2.0" in command


def test_build_soccernet_command_with_conda(monkeypatch, tmp_path: Path):
    _mock_assets(monkeypatch, tmp_path)
    conda = tmp_path / "conda.exe"
    conda.write_bytes(b"x")

    monkeypatch.setattr(fe, "SOCCERNET_EXECUTION_MODE", "conda")
    monkeypatch.setattr(fe, "SOCCERNET_EXTRACTOR_PYTHON", "")
    monkeypatch.setattr(fe, "SOCCERNET_CONDA_EXE", str(conda))
    monkeypatch.setattr(fe, "SOCCERNET_CONDA_ENV", "SoccerNet-FeatureExtraction")

    command = fe.build_soccernet_command(
        "input.mp4", "features.npy", fps=2, video_duration=10
    )
    assert command[:6] == [
        str(conda),
        "run",
        "--no-capture-output",
        "-n",
        "SoccerNet-FeatureExtraction",
        "python",
    ]
