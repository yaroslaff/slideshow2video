# slideshow2video

Store your photos (galleries) on youtube for free! (You can use "unlisted" visibility or even drafts to keep it private)

~~~bash
# create a slideshow (with music!) 
slideshow2video create /path/to/images -o output.mp4 -a /path/to/music_folder -d 4.0

# upload to youtube
# download  (use yt-dlp or just studio.youtube.com)

# extract images from video
slideshow2video extract -i /tmp/video_from_youtube.webm -o /tmp/extracted
~~~

## Warning
Vibe-coded for personal purpose. Do not expect much quality from this project. (I do not trust LLM as programmers). But it works for me.

## Installation

### Method 1: Installing via pipx (Recommended for CLI)
You can install the CLI tool globally and safely in an isolated environment directly from the Git repository:

```bash
pipx install git+https://github.com/yaroslaff/slideshow2video.git
```

### Method 2: Installing from source
Clone the repository and install it in editable mode:

```bash
git clone https://github.com/yaroslaff/slideshow2video.git
cd slideshow2video
pip install -e .
```

> **Note**: Audio muxing requires **FFmpeg** installed on your system and available in your environment path.

## CLI Usage

The `slideshow2video` command becomes globally accessible after installation.

### 1. Create a Slideshow (`create`)

Generate a stunning slideshow video from a directory of images and overlay background music:

```bash
slideshow2video create /path/to/images -o output.mp4 -a /path/to/music_folder -d 4.0
```

---

### 2. Extract Slides Back from Video (`extract`)

Extract original slides cleanly from any slideshow video made with marker frames:

```bash
slideshow2video extract -i output.mp4 -o /path/to/extracted_images
```

The extractor scans the video for background markers, detects clean slide boundaries, and exports the exact center frame of each segment as a high-quality `.jpg` file, bypassing transitional blur or movement issues.
