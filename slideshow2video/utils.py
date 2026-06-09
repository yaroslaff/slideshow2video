import argparse
import shutil
import subprocess

def check_ffmpeg():
    """Проверяет наличие установленного ffmpeg в системе."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "Программа 'ffmpeg' не найдена в PATH. Пожалуйста, установите FFmpeg "
            "для возможности наложения звука."
        )

def parse_color(color_str):
    """
    Парсит цвет из строки. Поддерживает имена цветов или формат R,G,B.
    Возвращает кортеж в формате BGR (стандарт для OpenCV).
    """
    colors = {
        "green": (0, 255, 0),
        "magenta": (255, 0, 255),
        "black": (0, 0, 0),
        "blue": (0, 0, 255),
        "red": (255, 0, 0)
    }
    color_str = color_str.lower().strip()
    if color_str in colors:
        rgb = colors[color_str]
    else:
        try:
            rgb = tuple(map(int, color_str.split(',')))
            if len(rgb) != 3:
                raise ValueError
        except Exception:
            raise argparse.ArgumentTypeError(
                "Цвет должен быть названием (green, magenta, black, blue, red) или в формате 'R,G,B'"
            )
    # Возвращаем BGR
    return (rgb[2], rgb[1], rgb[0])
