import math
import time


def format_bytes(
    size_bytes: int, precision: str = ".2f", postfix: str = "", base: int = 1024
) -> str:
    """将字节数格式化为人类可读形式"""
    if size_bytes == 0:
        return "0B"
    units = ("B", "KB", "MB", "GB", "TB", "PB")
    i = int(math.floor(math.log(size_bytes, base)))
    size = size_bytes / (base**i)
    return f"{size:{precision}}{units[i]}"


def format_ftime(seconds: float, format: str = "%Y-%m-%d %H:%M"):
    """将秒数格式化为日期和时间"""
    return time.strftime(format, time.localtime(seconds))
