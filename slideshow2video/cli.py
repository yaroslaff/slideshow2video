import argparse
import sys
from .creator import create_slideshow, collect_images, collect_audios
from .extractor import extract_slides
from .utils import parse_color

def main():
    parser = argparse.ArgumentParser(
        description="slideshow2video: Утилита для создания слайдшоу с эффектом Zoom-Pan и возможностью обратного извлечения слайдов."
    )
    
    subparsers = parser.add_subparsers(dest="mode", help="Режим работы")
    
    # Режим создания слайдшоу (create)
    create_parser = subparsers.add_parser("create", help="Создать видео из картинок")
    create_parser.add_argument("inputs", nargs="+", help="Пути к изображениям или директориям с ними")
    create_parser.add_argument("-o", "--output", required=True, help="Путь для сохранения готового MP4 файла")
    create_parser.add_argument("-a", "--audio", nargs="*", help="Пути к аудиофайлам или папкам с аудио (MP3, OGG, WAV)")
    create_parser.add_argument("-d", "--duration", type=float, default=5.0, help="Длительность показа каждого слайда в сек (по умолчанию: 5.0)")
    create_parser.add_argument("--fps", type=int, default=30, help="FPS выходного видео (по умолчанию: 30)")
    create_parser.add_argument("-r", "--resolution", default="1920x1080", help="Разрешение видео в формате WxH (по умолчанию: 1920x1080)")
    create_parser.add_argument("--zoom", action="store_true", help="Включить анимацию приближения (Zoom-Pan) с эффектом Ken Burns")
    create_parser.add_argument("--zoom-speed", type=float, default=1.15, help="Максимальный коэффициент приближения при активном зуме (по умолчанию: 1.15)")
    create_parser.add_argument("--marker-color", default="green", type=parse_color, 
                               help="Цвет маркера-разделителя между слайдами: green, magenta, black, blue, red или 'R,G,B' (по умолчанию: green)")
    create_parser.add_argument("--marker-duration", type=int, default=3, help="Количество маркерных кадров между слайдами (по умолчанию: 3)")
    
    # Режим извлечения картинок (extract)
    extract_parser = subparsers.add_parser("extract", help="Извлечь картинки из готового видео")
    extract_parser.add_argument("-i", "--input", required=True, help="Путь к исходному MP4 видео")
    extract_parser.add_argument("-o", "--output-dir", required=True, help="Директория для сохранения извлеченных слайдов")
    extract_parser.add_argument("--marker-color", default="green", type=parse_color, 
                               help="Цвет используемого при создании маркера: green, magenta, black, blue, red или 'R,G,B' (по умолчанию: green)")
    
    args = parser.parse_args()
    
    if not args.mode:
        parser.print_help()
        sys.exit(1)
        
    if args.mode == "create":
        images = collect_images(args.inputs)
        if not images:
            print("Ошибка: Не найдено поддерживаемых изображений.")
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
            print(f"Ошибка: Разрешение '{args.resolution}' должно быть алиасом (4k, 2k, 1080p, 720p, shorts) или в формате 'ширинаxвысота' (например, 1920x1080).")
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
            print(f"Ошибка при генерации слайдшоу: {e}")
            sys.exit(1)
            
    elif args.mode == "extract":
        try:
            extract_slides(
                video_path=args.input,
                output_dir=args.output_dir,
                marker_color=args.marker_color
            )
        except Exception as e:
            print(f"Ошибка при извлечении слайдов: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
