import argparse
import shutil
import subprocess

def check_ffmpeg():
    """Checks if ffmpeg is installed on the system."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "Command 'ffmpeg' was not found in PATH. Please install FFmpeg "
            "to support audio soundtrack mixing."
        )

def parse_color(color_str):
    """
    Parses color from string. Supports names of colors or R,G,B format.
    Returns BGR color tuple (standard for OpenCV).
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
                "Color must be a known color name (green, magenta, black, blue, red) or formatted as an 'R,G,B' string"
            )
    # Возвращаем BGR
    return (rgb[2], rgb[1], rgb[0])
