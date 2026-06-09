# slideshow2video

Build a YouTube-ready slideshow MP4 from a folder of photos and videos.

Files are sorted by modification time (`mtime`), so they appear in the order
they were taken — as long as you preserve timestamps when copying
(use `cp -a` and avoid tmpfs).

## Requirements

- Python 3.10+
- `ffmpeg` available in `$PATH`

```bash
# Ubuntu / Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

## Installation

```bash
pip install git+https://github.com/yaroslaff/slideshow2video
```

Or clone and install in editable mode:

```bash
git clone https://github.com/yaroslaff/slideshow2video
cd slideshow2video
pip install -e .
```

## Usage

```
slideshow2video <input_folder> [options]
```

| Option | Default | Description |
|---|---|---|
| `-o FILE` | `slideshow.mp4` | Output file |
| `-d SECS` | `5` | Seconds per slide |
| `-r PRESET` | `1080p` | Resolution: `720p`, `1080p`, `4k` |
| `--fps N` | `30` | Frames per second |
| `-t SECS` | `0.5` | Transition duration (0 = none) |
| `-a FILE` | — | Background audio (mp3/aac/wav) |
| `-q N` | `23` | CRF quality, 0–51 (lower = better) |
| `--zoom-pan` | off | Ken Burns zoom effect on images |
| `--recursive` | off | Search subdirectories recursively |
| `--list` | off | Preview file list without rendering |

### Examples

```bash
# Basic: 5 seconds per photo, 1080p
slideshow2video ./photos -o slideshow.mp4

# 3 seconds, 720p, background music
slideshow2video ./photos -d 3 -r 720p -a music.mp3 -o out.mp4

# 4K with Ken Burns effect and 1-second transition
slideshow2video ./photos -r 4k --zoom-pan -t 1.0 -o out4k.mp4

# Preview which files will be included (no render)
slideshow2video ./photos --list
```

## Supported formats

**Images:** jpg, jpeg, png, bmp, gif, tiff, webp  
**Videos:** mp4, mov, avi, mkv, webm, m4v

## Notes

- Output is encoded with H.264 + AAC and `-movflags +faststart` — ready to upload to YouTube without re-encoding.
- When using `--zoom-pan`, images are scaled to a 1.3× canvas first so the zoom never reveals black bars.
- If you copy photos with `cp -a`, make sure the destination is **not** on `tmpfs` — it resets all timestamps to the current time.

## License

MIT
