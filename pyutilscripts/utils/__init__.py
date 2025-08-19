import math
import time


def format_bytes(size_bytes: int, precision: int = 2) -> str:
    """自动将字节数格式化为人类可读的单位（B, KB, MB, GB...）"""
    if size_bytes == 0:
        return "0B"
    units = ("B", "KB", "MB", "GB", "TB", "PB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    size = size_bytes / (1024**i)
    return f"{size:.{precision}f}{units[i]}"


def format_ftime(seconds: float, format: str = "%y-%m-%d %H:%M"):
    """将秒数格式化为日期和时间"""
    return time.strftime(format, time.localtime(seconds))
