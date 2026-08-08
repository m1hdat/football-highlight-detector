from __future__ import annotations

import json
import os
import uuid
from typing import Dict, List, Tuple

from fastapi import UploadFile

from app.config import FEATURE_DIR, OUTPUT_DIR, UPLOAD_DIR
from app.utils.file_utils import (
    remove_if_exists,
    safe_makedirs,
    sanitize_filename,
    validate_job_id,
)


class UploadTooLargeError(ValueError):
    pass


def generate_job_id() -> str:
    return uuid.uuid4().hex[:12]


async def save_upload_file_stream(
    file: UploadFile,
    filename: str,
    job_id: str,
    max_bytes: int,
    chunk_size: int,
) -> Tuple[str, int]:
    """Lưu UploadFile theo từng chunk, không đọc toàn bộ video vào RAM."""
    validate_job_id(job_id)
    job_dir = get_upload_path(job_id)
    safe_makedirs(job_dir)
    safe_name = sanitize_filename(filename)
    video_path = os.path.join(job_dir, safe_name)
    total = 0

    try:
        with open(video_path, "wb") as output:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise UploadTooLargeError(f"File vượt quá giới hạn {max_bytes} bytes")
                output.write(chunk)
    except Exception:
        remove_if_exists(job_dir)
        raise
    finally:
        await file.close()

    if total == 0:
        remove_if_exists(job_dir)
        raise ValueError("File upload rỗng")
    return video_path, total


def get_upload_path(job_id: str) -> str:
    validate_job_id(job_id)
    return os.path.join(UPLOAD_DIR, job_id)


def get_feature_dir(job_id: str) -> str:
    validate_job_id(job_id)
    return os.path.join(FEATURE_DIR, job_id)


def get_feature_path(job_id: str) -> str:
    return os.path.join(get_feature_dir(job_id), "features.npy")


def get_output_dir(job_id: str, create: bool = True) -> str:
    validate_job_id(job_id)
    directory = os.path.join(OUTPUT_DIR, job_id)
    if create:
        safe_makedirs(directory)
    return directory


def save_result_json(job_id: str, results: List[Dict]) -> str:
    out_dir = get_output_dir(job_id, create=True)
    path = os.path.join(out_dir, "result.json")
    temp_path = f"{path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(results, file, ensure_ascii=False, indent=2)
    os.replace(temp_path, path)
    return path


def get_result_path(job_id: str) -> str:
    return os.path.join(get_output_dir(job_id, create=False), "result.json")


def has_result_json(job_id: str) -> bool:
    return os.path.isfile(get_result_path(job_id))


def load_result_json(job_id: str) -> List[Dict]:
    path = get_result_path(job_id)
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as file:
        data = json.load(file)
    return data if isinstance(data, list) else []


def cleanup_input_artifacts(job_id: str) -> None:
    """Xóa video gốc và feature sau khi đã tạo clip thành công."""
    remove_if_exists(get_upload_path(job_id))
    remove_if_exists(get_feature_dir(job_id))


def cleanup_all_job_artifacts(job_id: str) -> None:
    cleanup_input_artifacts(job_id)
    remove_if_exists(get_output_dir(job_id, create=False))
