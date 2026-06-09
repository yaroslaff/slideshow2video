import argparse
import sys
from .creator import create_slideshow, collect_images, collect_audios
from .extractor import extract_slides
from .utils import parse_color

def main():
    parser = argparse.ArgumentParser(
        description="slideshow2video: CLI tool to build high-quality slideshow videos with optional zoom-pan effects and reverse-extract slides."
    )
    
    subparsers = parser.add_subparsers(dest="mode", help="Working mode")
    
    # Slideshow Creation Mode (create)
    create_parser = subparsers.add_parser("create", help="Create a slideshow video from images")
    create_parser.add_argument("inputs", nargs="+", help="File paths of images or directories containing them")
    create_parser.add_argument("-o", "--output", required=True, help="Output path for the finished MP4 video file")
    create_parser.add_argument("-a", "--audio", nargs="*", help="File paths or directories containing music tracks (MP3, OGG, WAV, M4A)")
    create_parser.add_argument("-d", "--duration", type=float, default=5.0, help="Display duration of each slide in seconds (default: 5.0)")
    create_parser.add_argument("--fps", type=int, default=30, help="Framerate of the output video (default: 30)")
    create_parser.add_argument("-r", "--resolution", default="1920x1080", help="Video resolution. Accepts aliases (4k, 2k, 1080p, 720p, shorts) or standard WxH format (default: 1920x1080)")
    create_parser.add_argument("--zoom", action="store_true", help="Enable smooth Ken Burns diagonal zoom-pan animation effect")
    create_parser.add_argument("--zoom-speed", type=float, default=1.15, help="Maximum zoom scale factor when zoom is active (default: 1.15)")
    create_parser.add_argument("--marker-color", default="green", type=parse_color, 
                               help="Color of marker separators injected between slides: green, magenta, black, blue, red or 'R,G,B' (default: green)")
    create_parser.add_argument("--marker-duration", type=int, default=3, help="Number of blank marker frames injected between slides (default: 3)")
    
    # Reverse Extraction Mode (extract)
    extract_parser = subparsers.add_parser("extract", help="Extract static slide images back from a video")
    extract_parser.add_argument("-i", "--input", required=True, help="Input slideshow MP4 video file path")
    extract_parser.add_argument("-o", "--output-dir", required=True, help="Output directory folder to save the extracted slides")
    extract_parser.add_argument("--marker-color", default="green", type=parse_color, 
                               help="Marker separator color to identify boundaries: green, magenta, black, blue, red or 'R,G,B' (default: green)")
    
    args = parser.parse_args()
    
    if not args.mode:
        parser.print_help()
        sys.exit(1)
        
    if args.mode == "create":
        images = collect_images(args.inputs)
        if not images:
            print("Error: No supported images found in input files.")
            sys.exit(1)
            
        audios = collect_audios(args.audio) if args.audio else []
        
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
                marker_color=args.marker_color,
                marker_duration_frames=args.marker_duration,
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
                marker_color=args.marker_color
            )
        except Exception as e:
            print(f"Error extracting slides: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
