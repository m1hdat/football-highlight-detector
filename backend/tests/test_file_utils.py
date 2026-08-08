import pytest

from app.utils.file_utils import sanitize_filename, validate_clip_id, validate_job_id


def test_sanitize_filename_removes_path():
    assert sanitize_filename("../../my video.mp4") == "my_video.mp4"


def test_identifiers():
    assert validate_job_id("abcdef123456") == "abcdef123456"
    assert validate_clip_id("abcdef123456_goal_01") == "abcdef123456_goal_01"
    with pytest.raises(ValueError):
        validate_job_id("../bad")
