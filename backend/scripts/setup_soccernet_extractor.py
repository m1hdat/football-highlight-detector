"""Download the official SoccerNet TF2 feature extractor assets.

The files are pinned to a specific commit of SoccerNet/sn-spotting so every
team member uses the same extractor and PCA space.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
from pathlib import Path

REPOSITORY = "https://github.com/SoccerNet/sn-spotting"
COMMIT = "9842826f94e1419580a9d17219c11aca7225f7ce"
RAW_ROOT = f"https://raw.githubusercontent.com/SoccerNet/sn-spotting/{COMMIT}"

FILES = {
    "VideoFeatureExtractor.py": "Features/VideoFeatureExtractor.py",
    "pca_512_TF2.pkl": "Features/pca_512_TF2.pkl",
    "average_512_TF2.pkl": "Features/average_512_TF2.pkl",
    "SOCCERNET_LICENSE": "LICENSE",
    "SOCCERNET_FEATURES_README.md": "Features/README.md",
}

MIN_SIZE = {
    "VideoFeatureExtractor.py": 5_000,
    "pca_512_TF2.pkl": 1_000_000,
    "average_512_TF2.pkl": 1_000,
    "SOCCERNET_LICENSE": 500,
    "SOCCERNET_FEATURES_README.md": 500,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path, force: bool = False) -> None:
    if destination.exists() and not force:
        print(f"[skip] {destination.name} already exists")
        return

    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "football-highlight-cutter/1.0"},
    )
    with tempfile.NamedTemporaryFile(delete=False, dir=destination.parent) as temp:
        temp_path = Path(temp.name)
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                shutil.copyfileobj(response, temp)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

    if temp_path.stat().st_size < MIN_SIZE[destination.name]:
        size = temp_path.stat().st_size
        temp_path.unlink(missing_ok=True)
        raise RuntimeError(
            f"Downloaded {destination.name} is unexpectedly small ({size} bytes)"
        )
    os.replace(temp_path, destination)
    print(f"[ok] {destination.name}: {destination.stat().st_size:,} bytes")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--destination",
        default=str(
            Path(__file__).resolve().parents[1] / "third_party" / "soccernet_features"
        ),
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    destination = Path(args.destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)

    for local_name, repository_path in FILES.items():
        download(
            f"{RAW_ROOT}/{repository_path}",
            destination / local_name,
            force=args.force,
        )

    manifest = {
        "repository": REPOSITORY,
        "commit": COMMIT,
        "source": f"{REPOSITORY}/tree/{COMMIT}/Features",
        "files": {},
    }
    for local_name, repository_path in FILES.items():
        path = destination / local_name
        manifest["files"][local_name] = {
            "repository_path": repository_path,
            "size": path.stat().st_size,
            "sha256": sha256(path),
        }

    manifest_path = destination / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[ok] manifest: {manifest_path}")
    print("\nNext: create or update the SoccerNet Conda environment.")
    print("The backend uses 'conda run' by default; no Python path is required.")


if __name__ == "__main__":
    main()
