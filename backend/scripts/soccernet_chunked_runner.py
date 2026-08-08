"""Memory-bounded runner around SoccerNet's official TF2 extractor.

This file is executed with the dedicated SoccerNet Python environment. It
imports the official `VideoFeatureExtractor` and `PCAReducer`, loads ResNet-152
once, processes a long video in time chunks, then concatenates official
PCA512 outputs into a single `[T, 512]` array.
"""

from __future__ import annotations

import argparse
import math
import os
import sys
import tempfile
from pathlib import Path

import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path_video", required=True)
    parser.add_argument("--path_features", required=True)
    parser.add_argument("--video_duration", required=True, type=float)
    parser.add_argument("--chunk_duration", type=float, default=300.0)
    parser.add_argument("--fps", type=float, default=2.0)
    parser.add_argument("--gpu", type=int, default=-1)
    parser.add_argument("--transform", default="crop")
    parser.add_argument("--grabber", default="opencv")
    parser.add_argument("--extractor_dir", required=True)
    parser.add_argument("--pca", required=True)
    parser.add_argument("--pca_scaler", required=True)
    args = parser.parse_args()

    if args.video_duration <= 0:
        raise ValueError("video_duration must be positive")
    if args.chunk_duration <= 0:
        raise ValueError("chunk_duration must be positive")

    os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    os.environ["CUDA_VISIBLE_DEVICES"] = str(args.gpu)

    extractor_dir = str(Path(args.extractor_dir).resolve())
    sys.path.insert(0, extractor_dir)
    from VideoFeatureExtractor import PCAReducer, VideoFeatureExtractor

    extractor = VideoFeatureExtractor(
        feature="ResNET",
        back_end="TF2",
        transform=args.transform,
        grabber=args.grabber,
        FPS=args.fps,
    )
    reducer = PCAReducer(pca_file=args.pca, scaler_file=args.pca_scaler)

    outputs = []

    # ffprobe may report a tiny fractional tail for an exact-length video,
    # for example 2700.04 seconds for a 45:00 half. With ceil(), that tail
    # becomes an extra chunk. FrameCV then returns zero sampled frames and
    # TensorFlow's preprocess_input raises IndexError. Align the duration to
    # the feature sampling grid and tolerate an empty final tail chunk.
    feature_interval = 1.0 / args.fps
    effective_duration = (
        math.floor((args.video_duration + 1e-6) / feature_interval)
        * feature_interval
    )
    chunk_count = int(math.ceil(effective_duration / args.chunk_duration))

    with tempfile.TemporaryDirectory(prefix="soccernet_features_") as temp_dir:
        for index in range(chunk_count):
            start = index * args.chunk_duration
            remaining = effective_duration - start
            if remaining < feature_interval:
                print(
                    f"[chunk {index + 1}/{chunk_count}] skipping tiny tail "
                    f"({remaining:.3f}s)",
                    flush=True,
                )
                break

            duration = min(args.chunk_duration, remaining)
            chunk_path = os.path.join(temp_dir, f"chunk_{index:04d}.npy")
            print(
                f"[chunk {index + 1}/{chunk_count}] start={start:.3f}s "
                f"duration={duration:.3f}s",
                flush=True,
            )

            try:
                extractor.extractFeatures(
                    path_video_input=args.path_video,
                    path_features_output=chunk_path,
                    start=start,
                    duration=duration,
                    overwrite=True,
                )
            except IndexError:
                # OpenCV/SoccerNet may return no sampled frame for a tiny
                # metadata-only tail at the very end of MKV files. Previous
                # chunks are valid, so do not discard the whole extraction.
                if index == chunk_count - 1:
                    print(
                        f"[chunk {index + 1}/{chunk_count}] empty final tail; "
                        "keeping previous chunks",
                        flush=True,
                    )
                    break
                raise

            if not os.path.isfile(chunk_path):
                if index == chunk_count - 1:
                    print(
                        f"[chunk {index + 1}/{chunk_count}] no output for "
                        "final tail; keeping previous chunks",
                        flush=True,
                    )
                    break
                raise RuntimeError(f"SoccerNet did not create chunk: {chunk_path}")

            raw_chunk = np.load(chunk_path)
            if raw_chunk.ndim != 2:
                raise ValueError(
                    f"Invalid raw SoccerNet chunk shape: {raw_chunk.shape}"
                )
            if raw_chunk.shape[0] == 0:
                if index == chunk_count - 1:
                    print(
                        f"[chunk {index + 1}/{chunk_count}] zero-frame final "
                        "tail; keeping previous chunks",
                        flush=True,
                    )
                    break
                raise RuntimeError(
                    f"SoccerNet returned an empty non-final chunk at index {index}"
                )

            reducer.reduceFeatures(
                input_features=chunk_path,
                output_features=chunk_path,
                overwrite=True,
            )
            chunk = np.load(chunk_path)
            if chunk.ndim != 2 or chunk.shape[1] != 512:
                raise ValueError(f"Invalid SoccerNet chunk shape: {chunk.shape}")
            outputs.append(chunk.astype(np.float32, copy=False))

    if not outputs:
        raise RuntimeError("SoccerNet extractor returned no feature vectors")

    features = np.concatenate(outputs, axis=0).astype(np.float32, copy=False)
    output = Path(args.path_features)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.save(str(output), features)
    print(f"Saved official SoccerNet features {features.shape} to {output}", flush=True)


if __name__ == "__main__":
    main()