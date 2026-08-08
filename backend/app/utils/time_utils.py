def format_time(seconds: float) -> str:
    """Đổi giây -> 'MM:SS' để in log/hiển thị."""
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    return f"{m:02d}:{s:02d}"


def second_to_index(second: float, fps: int) -> int:
    """Đổi timestamp (giây) sang index trong mảng feature."""
    return int(round(second * fps))


def index_to_second(index: int, fps: int) -> float:
    """Đổi index feature sang giây."""
    return index / float(fps)
