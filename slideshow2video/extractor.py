import cv2
import numpy as np
import os
from tqdm import tqdm

def is_marker_frame(frame, marker_color=(0, 255, 0), tolerance=15):
    """
    Проверяет, является ли кадр маркерным.
    Анализирует средний цвет кадра и его стандартное отклонение (для проверки однотонности).
    Это обеспечивает защиту от ложных срабатываний и устойчивость к потерям сжатия.
    """
    mean_bgr = np.mean(frame, axis=(0, 1))
    dist = np.linalg.norm(mean_bgr - marker_color)
    if dist > tolerance:
        return False
    
    # Стандартное отклонение должно быть близко к нулю (абсолютно плоский цвет)
    std_bgr = np.std(frame, axis=(0, 1))
    if np.max(std_bgr) > 5.0:
        return False
        
    return True

def extract_slides(video_path, output_dir, marker_color=(0, 255, 0)):
    """Extracts original slides from video, saving the clean center frame of each segment."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")
        
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    os.makedirs(output_dir, exist_ok=True)
    
    print("Pass 1: Searching for slide boundary markers...")
    slide_segments = []
    current_segment = []
    frame_idx = 0
    
    pbar = tqdm(total=total_frames, desc="Analyzing video")
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if is_marker_frame(frame, marker_color):
            if current_segment:
                slide_segments.append(current_segment)
                current_segment = []
        else:
            current_segment.append(frame_idx)
            
        frame_idx += 1
        pbar.update(1)
    pbar.close()
    
    if current_segment:
        slide_segments.append(current_segment)
        
    cap.release()
    
    # Prune extra-short transitions (noise under 5 frames)
    valid_segments = [seg for seg in slide_segments if len(seg) >= 5]
    
    if not valid_segments:
        print("No slides detected. Please verify your marker color settings.")
        return []
        
    print(f"Found {len(valid_segments)} slides. Extracting clean center frames...")
    
    # Grab the middle frame of each segment to avoid transition/blend remnants
    target_frames = {seg[len(seg) // 2]: idx for idx, seg in enumerate(valid_segments)}
    
    # Pass 2: Extract selected frames
    cap = cv2.VideoCapture(str(video_path))
    frame_idx = 0
    pbar = tqdm(total=total_frames, desc="Exporting images")
    
    saved_paths = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_idx in target_frames:
            slide_num = target_frames[frame_idx]
            out_path = os.path.join(output_dir, f"extracted_slide_{slide_num:03d}.jpg")
            cv2.imwrite(out_path, frame)
            saved_paths.append(out_path)
            
        frame_idx += 1
        pbar.update(1)
        
    pbar.close()
    cap.release()
    print(f"Extraction completed! Images saved inside: '{output_dir}'.")
    return saved_paths
