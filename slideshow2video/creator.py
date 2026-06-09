import cv2
import numpy as np
import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from tqdm import tqdm
from .utils import check_ffmpeg

def crop_to_fill(img, target_width, target_height):
    """Обрезает и масштабирует изображение под целевое соотношение сторон без искажений."""
    h, w = img.shape[:2]
    target_aspect = target_width / target_height
    aspect = w / h
    
    if aspect > target_aspect:
        # Изображение шире целевого формата -> обрезаем по бокам
        new_width = int(h * target_aspect)
        start_x = (w - new_width) // 2
        cropped = img[:, start_x:start_x+new_width]
    else:
        # Изображение выше целевого формата -> обрезаем сверху/снизу
        new_height = int(w / target_aspect)
        start_y = (h - new_height) // 2
        cropped = img[start_y:start_y+new_height, :]
        
    return cv2.resize(cropped, (target_width, target_height))

def get_zoomed_frame(img, progress, max_zoom=1.15):
    """
    Создает эффект динамического приближения (Zoom-Pan) с легким
    диагональным смещением центра кадра для дополнительной динамики.
    """
    h, w = img.shape[:2]
    zoom_factor = 1.0 + progress * (max_zoom - 1.0)
    
    # Размер кадрируемой области под зум
    new_h, new_w = int(h / zoom_factor), int(w / zoom_factor)
    
    # Вычисляем максимальное смещение
    max_shift_y = h - new_h
    max_shift_x = w - new_w
    
    # Плавное диагональное панорамирование (от верхнего левого к нижнему правому)
    shift_y = int(progress * max_shift_y)
    shift_x = int(progress * max_shift_x)
    
    cropped = img[shift_y:shift_y+new_h, shift_x:shift_x+new_w]
    return cv2.resize(cropped, (w, h))

def collect_images(inputs):
    """Рекурсивно или точечно собирает все поддерживаемые изображения."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
    collected = []
    for inp in inputs:
        p = Path(inp)
        if p.is_dir():
            for file in sorted(p.iterdir()):
                if file.suffix.lower() in image_extensions:
                    collected.append(file)
        elif p.is_file():
            if p.suffix.lower() in image_extensions:
                collected.append(p)
    return collected

def collect_audios(audio_inputs):
    """Рекурсивно или точечно собирает все поддерживаемые аудиофайлы."""
    audio_extensions = {'.mp3', '.ogg', '.wav', '.m4a'}
    collected = []
    if not audio_inputs:
        return collected
    for inp in audio_inputs:
        p = Path(inp)
        if p.is_dir():
            for file in sorted(p.iterdir()):
                if file.suffix.lower() in audio_extensions:
                    collected.append(file)
        elif p.is_file():
            if p.suffix.lower() in audio_extensions:
                collected.append(p)
    return collected

def mux_audio(video_path, audio_files, output_path):
    """Склеивает аудиофайлы, зацикливает их под длину видео и объединяет видео со звуком."""
    check_ffmpeg()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        
        if len(audio_files) > 1:
            # Если файлов несколько, подготавливаем concat-лист для FFmpeg
            concat_list_path = temp_dir_path / "concat.txt"
            with open(concat_list_path, "w", encoding="utf-8") as f:
                for audio in audio_files:
                    escaped_path = str(Path(audio).resolve()).replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")
            
            temp_combined_audio = temp_dir_path / "combined.mp3"
            concat_cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", str(concat_list_path), "-c", "copy", str(temp_combined_audio)
            ]
            subprocess.run(concat_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            audio_to_use = temp_combined_audio
        else:
            audio_to_use = Path(audio_files[0]).resolve()
            
        # Накладываем аудио на видео с зацикливанием (-stream_loop -1) и обрезанием под длину видео (-shortest)
        mux_cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-stream_loop", "-1", "-i", str(audio_to_use),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(output_path)
        ]
        # Обратите внимание: мы поменяли copy видео на libx264 и yuv420p для 100% совместимости с YouTube и браузерами
        subprocess.run(mux_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def create_slideshow(
    images,
    output_path,
    duration=5.0,
    fps=30,
    resolution=(1920, 1080),
    zoom=False,
    zoom_speed=1.15,
    marker_color=(0, 255, 0),
    marker_duration_frames=3,
    audio_files=None
):
    """Создает видеофайл из переданных картинок."""
    width, height = resolution
    # Используем avc1/mp4v или mp4v
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    
    # Создаем временный файл для чернового видео без аудио
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video:
        temp_video_path = temp_video.name
        
    out = cv2.VideoWriter(temp_video_path, fourcc, fps, (width, height))
    frames_per_slide = int(duration * fps)
    
    print(f"Building video stream ({len(images)} slides, {fps} FPS)...")
    for img_path in tqdm(images, desc="Rendering frames"):
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"\nWarning: Could not read image {img_path}. Skipping.")
            continue
            
        prepared_img = crop_to_fill(img, width, height)
        
        # Generation of frames for the current slide
        for i in range(frames_per_slide):
            if zoom:
                progress = i / max(1, frames_per_slide - 1)
                frame = get_zoomed_frame(prepared_img, progress, max_zoom=zoom_speed)
            else:
                frame = prepared_img.copy()
            out.write(frame)
            
        # Add blank marker separator frames (for future extraction)
        if marker_duration_frames > 0:
            marker_frame = np.full((height, width, 3), marker_color, dtype=np.uint8)
            for _ in range(marker_duration_frames):
                out.write(marker_frame)
                
    out.release()
    
    # Layering audio soundtrack (if provided)
    if audio_files:
        print("Processing and mixing audio...")
        try:
            mux_audio(temp_video_path, audio_files, output_path)
        except Exception as e:
            print(f"\nError during audio mixing: {e}")
            print("Saving video without audio.")
            # Re-encode to libx264/yuv420p via ffmpeg
            try:
                subprocess.run([
                    "ffmpeg", "-y", "-i", temp_video_path, "-c:v", "libx264", "-pix_fmt", "yuv420p", str(output_path)
                ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except Exception:
                if os.path.exists(output_path):
                    os.remove(output_path)
                shutil.move(temp_video_path, output_path)
        finally:
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)
    else:
        # Re-encode video as h264 for active web support
        try:
            subprocess.run([
                "ffmpeg", "-y", "-i", temp_video_path, "-c:v", "libx264", "-pix_fmt", "yuv420p", str(output_path)
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception:
            if os.path.exists(output_path):
                os.remove(output_path)
            shutil.move(temp_video_path, output_path)
        finally:
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)
        
    print(f"Done! Video successfully saved to: {output_path}")
