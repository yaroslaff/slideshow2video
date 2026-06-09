#!/usr/bin/env python3
"""
slideshow_to_video.py — builds a slideshow MP4 from a folder of photos/videos.

Requirements: ffmpeg (system), no Python dependencies beyond stdlib.
"""

import argparse
import subprocess
import sys
import re
import tempfile
import shutil
from pathlib import Path

# --------------------------------------------------------------------------- #
# Supported extensions
# --------------------------------------------------------------------------- #
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tiff", ".tif", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
ALL_EXTS   = IMAGE_EXTS | VIDEO_EXTS

# YouTube-friendly resolution presets
YT_PRESETS = {
    "720p":  (1280, 720),
    "1080p": (1920, 1080),
    "4k":    (3840, 2160),
}

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        sys.exit("❌  ffmpeg not found. Install it: sudo apt install ffmpeg")


def collect_files(src: Path, recursive: bool) -> list[Path]:
    glob = src.rglob("*") if recursive else src.glob("*")
    files = sorted(
        (f for f in glob if f.is_file() and f.suffix.lower() in ALL_EXTS),
        key=lambda p: p.stat().st_mtime,
    )
    return files


# --------------------------------------------------------------------------- #
# Core
# --------------------------------------------------------------------------- #

def build_video(
    files: list[Path],
    output: Path,
    duration: float,
    resolution: tuple[int, int],
    fps: int,
    transition: float,
    audio: Path | None,
    quality: int,
    zoom_pan: bool,
):
    w, h = resolution
    tmp = Path(tempfile.mkdtemp(prefix="slideshow_"))
    concat_list = tmp / "concat.txt"

    print(f"\n📂  Files found:   {len(files)}")
    print(f"🎬  Resolution:    {w}×{h} @ {fps} fps")
    print(f"⏱   Slide duration: {duration}s, transition: {transition}s")
    print(f"💾  Output:        {output}\n")

    try:
        lines = []

        for i, f in enumerate(files):
            ext = f.suffix.lower()
            clip = tmp / f"clip_{i:05d}.mp4"

            if ext in IMAGE_EXTS:
                if zoom_pan:
                    # Ken Burns effect:
                    # Scale image into a 1.3× canvas preserving aspect ratio,
                    # then zoompan crops back to target resolution — no distortion.
                    zw, zh = w * 13 // 10, h * 13 // 10
                    zw += zw % 2  # must be even
                    zh += zh % 2
                    frames = int(fps * duration)
                    vf_parts = [
                        f"scale={zw}:{zh}:force_original_aspect_ratio=decrease",
                        f"pad={zw}:{zh}:(ow-iw)/2:(oh-ih)/2:black",
                        f"zoompan=z='min(zoom+0.0008,1.3)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                        f":d={frames}:s={w}x{h}:fps={fps}",
                        "format=yuv420p",
                    ]
                else:
                    vf_parts = [
                        f"scale={w}:{h}:force_original_aspect_ratio=decrease",
                        f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black",
                        "format=yuv420p",
                    ]

                cmd = [
                    "ffmpeg", "-y", "-loop", "1", "-i", str(f),
                    "-t", str(duration + transition),
                    "-vf", ",".join(vf_parts),
                    "-c:v", "libx264", "-preset", "fast",
                    "-crf", str(quality),
                    "-r", str(fps),
                    str(clip),
                ]
                _run(cmd, f"Image  {f.name}")

            else:
                # Video clip: normalize resolution, drop audio (added later)
                vf = (
                    f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
                    f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black,"
                    "format=yuv420p"
                )
                cmd = [
                    "ffmpeg", "-y", "-i", str(f),
                    "-vf", vf,
                    "-c:v", "libx264", "-preset", "fast",
                    "-crf", str(quality),
                    "-r", str(fps),
                    "-an",
                    str(clip),
                ]
                _run(cmd, f"Video  {f.name}")

            lines.append(f"file '{clip}'\n")

        # Write concat list
        concat_list.write_text("".join(lines))

        # Merge all clips
        merged = tmp / "merged.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c:v", "libx264", "-preset", "medium",
            "-crf", str(quality),
            "-movflags", "+faststart",  # YouTube: moov atom at the start
        ]

        if audio:
            cmd += ["-i", str(audio), "-c:a", "aac", "-b:a", "192k",
                    "-shortest", "-map", "0:v:0", "-map", "1:a:0"]
        else:
            cmd += ["-an"]

        cmd.append(str(merged))
        _run(cmd, "Merging final video")

        shutil.copy2(merged, output)
        size_mb = output.stat().st_size / 1024 / 1024
        print(f"\n✅  Done! {output}  ({size_mb:.1f} MB)")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _run(cmd: list, label: str):
    print(f"  ⚙️   {label}…")
    result = subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        print("ffmpeg error:")
        print(result.stderr[-2000:])
        sys.exit(1)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def parse_args():
    p = argparse.ArgumentParser(
        description="Build a YouTube-ready slideshow video from a folder of photos/videos.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic: 5 seconds per slide, 1080p
  slideshow2video ./photos -o slideshow.mp4

  # 3 seconds per slide, 720p, with background music
  slideshow2video ./photos -d 3 -r 720p -a music.mp3 -o out.mp4

  # 4K with Ken Burns effect and 1-second transition
  slideshow2video ./photos -r 4k --zoom-pan -t 1.0 -o out4k.mp4

  # Preview which files will be included (no render)
  slideshow2video ./photos --list
""",
    )
    p.add_argument("input",
                   type=Path, help="Folder with photos/videos")
    p.add_argument("-o", "--output",
                   type=Path, default=Path("slideshow.mp4"),
                   help="Output file (default: slideshow.mp4)")
    p.add_argument("-d", "--duration",
                   type=float, default=5.0,
                   help="Seconds per slide (default: 5)")
    p.add_argument("-r", "--resolution",
                   default="1080p", choices=list(YT_PRESETS.keys()),
                   help="Output resolution (default: 1080p)")
    p.add_argument("--fps",
                   type=int, default=30,
                   help="Frames per second (default: 30)")
    p.add_argument("-t", "--transition",
                   type=float, default=0.5,
                   help="Transition duration in seconds (default: 0.5; 0 = none)")
    p.add_argument("-a", "--audio",
                   type=Path, default=None,
                   help="Background audio file (mp3/aac/wav)")
    p.add_argument("-q", "--quality",
                   type=int, default=23,
                   help="CRF quality 0-51: lower = better (default: 23)")
    p.add_argument("--zoom-pan",
                   action="store_true",
                   help="Ken Burns zoom effect on images")
    p.add_argument("--recursive",
                   action="store_true",
                   help="Search for files recursively in subdirectories")
    p.add_argument("--list",
                   action="store_true",
                   help="List files that would be used, then exit")
    return p.parse_args()


def main():
    args = parse_args()
    check_ffmpeg()

    src = args.input
    if not src.is_dir():
        sys.exit(f"❌  Directory not found: {src}")

    files = collect_files(src, args.recursive)
    if not files:
        sys.exit(
            f"❌  No supported files found in {src}\n"
            f"   Supported formats: {', '.join(sorted(ALL_EXTS))}"
        )

    if args.list:
        print(f"Found {len(files)} file(s):")
        for f in files:
            print(f"  {f}")
        return

    if args.audio and not args.audio.is_file():
        sys.exit(f"❌  Audio file not found: {args.audio}")

    build_video(
        files      = files,
        output     = args.output,
        duration   = args.duration,
        resolution = YT_PRESETS[args.resolution],
        fps        = args.fps,
        transition = args.transition,
        audio      = args.audio,
        quality    = args.quality,
        zoom_pan   = args.zoom_pan,
    )


if __name__ == "__main__":
    main()
