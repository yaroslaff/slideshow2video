import argparse
import sys
from . import __version__
from .creator import create_slideshow, collect_images, collect_audios
from .extractor import extract_slides
from .utils import parse_color

def auto_detect_resolution(images):
    # Use fast PIL/Pillow metadata reads to avoid loading whole pixel arrays
    try:
        from PIL import Image
        use_pil = True
    except ImportError:
        use_pil = False
        import cv2

    max_w = 0
    max_h = 0
    for img_path in images:
        if use_pil:
            try:
                with Image.open(str(img_path)) as img:
                    w, h = img.size
                    max_w = max(max_w, w)
                    max_h = max(max_h, h)
            except Exception:
                try:
                    img = cv2.imread(str(img_path))
                    if img is not None:
                        max_w = max(max_w, img.shape[1])
                        max_h = max(max_h, img.shape[0])
                except Exception:
                    pass
        else:
            try:
                img = cv2.imread(str(img_path))
                if img is not None:
                    max_w = max(max_w, img.shape[1])
                    max_h = max(max_h, img.shape[0])
            except Exception:
                pass
            
    if max_w == 0 or max_h == 0:
        # Fallback if no images could be read
        return 1920, 1080

    # Cap auto-detected resolution at a highly-compatible 4K profile (3840x2160 or 2160x3840)
    # to avoid extreme slowness and H.264 profile level failures during encoding.
    is_portrait = max_h > max_w
    if is_portrait:
        # Portrait cap
        if max_w > 2160 or max_h > 3840:
            print(f"Auto-detect: Original max resolution ({max_w}x{max_h}) capped at portrait 2160x3840 for speed and compatibility.")
            max_w = min(max_w, 2160)
            max_h = min(max_h, 3840)
    else:
        # Landscape/square cap
        if max_w > 3840 or max_h > 2160:
            print(f"Auto-detect: Original max resolution ({max_w}x{max_h}) capped at landscape 3840x2160 for speed and compatibility.")
            max_w = min(max_w, 3840)
            max_h = min(max_h, 2160)
        
    POPULAR_RESOLUTIONS = [
        (640, 360),
        (854, 480),
        (1280, 720),
        (1920, 1080),
        (2560, 1440),
        (3840, 2160),
        # Portrait equivalents
        (360, 640),
        (480, 854),
        (720, 1280),
        (1080, 1920),
        (1440, 2560),
        (2160, 3840)
    ]
    
    # We want a standard popular resolution (W, H) such that W >= max_w and H >= max_h
    candidates = [res for res in POPULAR_RESOLUTIONS if res[0] >= max_w and res[1] >= max_h]
    
    if candidates:
        # Choose the candidate with the smallest area among those that fit
        candidates.sort(key=lambda x: x[0] * x[1])
        chosen_w, chosen_h = candidates[0]
    else:
        # If no popular resolution is large enough, use the maximum image dimensions
        # and ensure even numbers for encoder compatibility (required by H264)
        chosen_w = max_w if max_w % 2 == 0 else max_w + 1
        chosen_h = max_h if max_h % 2 == 0 else max_h + 1
        
    print(f"Auto-detected resolution from images: {chosen_w}x{chosen_h} (max photo size was {max_w}x{max_h})")
    return chosen_w, chosen_h

def main():
    parser = argparse.ArgumentParser(
        description=f"slideshow2video v{__version__}: CLI tool to build high-quality slideshow videos with optional zoom-pan effects and reverse-extract slides."
    )
    parser.add_argument("-v", "--version", action="version", version=f"slideshow2video v{__version__}")
    
    subparsers = parser.add_subparsers(dest="mode", help="Working mode")
    
    # Slideshow Creation Mode (create)
    create_parser = subparsers.add_parser(
        "create", 
        help="Create a slideshow video from images",
        description=f"slideshow2video v{__version__}: Command to build high-quality slideshow videos with optional zoom-pan effects."
    )
    create_parser.add_argument("inputs", nargs="*", help="File paths of images or directories containing them. Optional if --from-file is provided.")
    create_parser.add_argument("-o", "--output", required=True, help="Output path for the finished MP4 video file")
    create_parser.add_argument("-a", "--audio", nargs="*", help="File paths or directories containing music tracks (MP3, OGG, WAV, M4A)")
    create_parser.add_argument("-d", "--duration", type=float, default=5.0, help="Display duration of each slide in seconds (default: 5.0)")
    create_parser.add_argument("--fps", type=int, default=30, help="Framerate of the output video (default: 30)")
    create_parser.add_argument("-r", "--resolution", default=None, help="Video resolution. Accepts aliases (4k, 2k, 1080p, 720p, shorts), standard WxH, or None/auto to match the largest image size (default: auto)")
    create_parser.add_argument("--zoom", action="store_true", help="Enable smooth Ken Burns diagonal zoom-pan animation effect")
    create_parser.add_argument("--zoom-speed", type=float, default=1.15, help="Maximum zoom scale factor when zoom is active (default: 1.15)")
    create_parser.add_argument("--sort", choices=["name", "mtime", "none"], default="name",
                               help="Sort order of collected files: 'name' (alphabetical), 'mtime' (modification time), or 'none' (keeps list/input order) (default: name)")
    create_parser.add_argument("-f", "--from-file", "--list-file", dest="list_file",
                               help="Text file containing list of image paths (one per line) to be used as slideshow slides.")
    create_parser.add_argument("-l", "--limit", type=int, default=None, help="Limit processing to the first N images (useful for quick debugging)")
    
    # Reverse Extraction Mode (extract)
    extract_parser = subparsers.add_parser(
        "extract", 
        help="Extract static slide images back from a video",
        description=f"slideshow2video v{__version__}: Command to reverse-extract slide images from completed slideshow videos."
    )
    extract_parser.add_argument("-i", "--input", required=True, help="Input slideshow MP4 video file path")
    extract_parser.add_argument("-o", "--output-dir", required=True, help="Output directory folder to save the extracted slides")
    extract_parser.add_argument("-d", "--duration", type=float, default=None, 
                               help="[Optional Time-based Mode] Duration of each slide in seconds. Enables pixel-free math extraction.")
    extract_parser.add_argument("--fps", type=int, default=None, 
                               help="[Optional Time-based Mode] Video framerate. Auto-detected from video file if left empty.")
    
    args = parser.parse_args()
    
    if not args.mode:
        parser.print_help()
        sys.exit(1)
        
    try:
        if args.mode == "create":
            if not args.inputs and not args.list_file:
                print("Error: You must provide either input files/directories, or a list file using --from-file.")
                sys.exit(1)
                
            sort_by = "none" if args.list_file else args.sort
            images = collect_images(args.inputs, sort_by=sort_by, list_file=args.list_file)
            if not images:
                print("Error: No supported images found in input files.")
                sys.exit(1)
                
            if args.limit is not None and args.limit > 0:
                print(f"Debug Mode: Limiting input to the first {args.limit} images.")
                images = images[:args.limit]
                
            audios = collect_audios(args.audio) if args.audio else []
            
            if args.resolution is None or args.resolution.lower().strip() in ("", "none", "auto"):
                width, height = auto_detect_resolution(images)
            else:
                res_alias = args.resolution.lower().strip()
                aliases = {
                    "4k": "3840x2160",
                    "2k": "2560x1440",
                    "1080p": "1920x1080",
                    "720p": "1280x720",
                    "480p": "854x480",
                    "360p": "640x360",
                    "shorts": "1080x1920"
                }
                res_str = aliases.get(res_alias, args.resolution)
                
                try:
                    width, height = map(int, res_str.lower().split("x"))
                except ValueError:
                    print(f"Error: Resolution '{args.resolution}' must be a supported alias (4k, 2k, 1080p, 720p, shorts) or in WxH format (e.g., 1920x1080).")
                    sys.exit(1)
                
            try:
                create_slideshow(
                    images=images,
                    output_path=args.output,
                    duration=args.duration,
                    fps=args.fps,
                    resolution=(width, height),
                    zoom=args.zoom,
                    zoom_speed=args.zoom_speed,
                    audio_files=audios
                )
            except Exception as e:
                print(f"Error compiling slideshow: {e}")
                sys.exit(1)
                
        elif args.mode == "extract":
            try:
                extract_slides(
                    video_path=args.input,
                    output_dir=args.output_dir,
                    duration=args.duration,
                    fps=args.fps
                )
            except Exception as e:
                print(f"Error extracting slides: {e}")
                sys.exit(1)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting...")
        sys.exit(1)

if __name__ == "__main__":
    main()
