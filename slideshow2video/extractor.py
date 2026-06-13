import cv2
import numpy as np
import os
from tqdm import tqdm

def crop_black_borders(img, val_threshold=20, ratio_threshold=0.98):
    """
    Crops black borders (letterboxing/pillarboxing) from an image.
    Scans row-by-row and col-by-col from the edges to find where actual content begins.
    """
    if img is None:
        return img
        
    h, w = img.shape[:2]
    if h == 0 or w == 0:
        return img
        
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Calculate fraction of dark pixels for each row and column
    black_rows = np.mean(gray < val_threshold, axis=1) >= ratio_threshold
    black_cols = np.mean(gray < val_threshold, axis=0) >= ratio_threshold
    
    top = 0
    while top < h and black_rows[top]:
        top += 1
        
    bottom = h
    while bottom > top and black_rows[bottom - 1]:
        bottom -= 1
        
    left = 0
    while left < w and black_cols[left]:
        left += 1
        
    right = w
    while right > left and black_cols[right - 1]:
        right -= 1
        
    cropped_h = bottom - top
    cropped_w = right - left
    
    # Safety fallback to avoid over-cropping dark slide designs
    if cropped_h < h * 0.1 or cropped_w < w * 0.1:
        return img
        
    if top == 0 and bottom == h and left == 0 and right == w:
        return img
        
    return img[top:bottom, left:right]

def auto_detect_slide_duration(video_path, fps):
    """
    Scans the video to auto-detect the constant slide duration (in seconds).
    To be extremely fast, it reads a compact sample of frames from the beginning
    sequentially (using fast .grab() for skipped frames) and detects peak visual differences (slide changes).
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return 5.0
        
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    # We sample up to the first 2400 frames (e.g., 1.3 minutes at 30 fps),
    # which is plenty to gather a statistically robust slide duration.
    max_scan_frames = min(total_frames, 2400)
    
    diffs = []
    prev_gray = None
    frame_indices = []
    
    # We read sequentially with step limit to avoid slow random seeks (.set)
    step = 5
    f = 0
    pbar = tqdm(total=max_scan_frames, desc="Analyzing video timing sequentially")
    while f < max_scan_frames:
        if f % step == 0:
            ret, frame = cap.read()
            if not ret:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_sm = cv2.resize(gray, (80, 45), interpolation=cv2.INTER_AREA)
            
            if prev_gray is not None:
                diff = np.mean(np.abs(gray_sm.astype(np.float32) - prev_gray.astype(np.float32)))
                diffs.append(diff)
            else:
                diffs.append(0.0)
                
            frame_indices.append(f)
            prev_gray = gray_sm
            f += 1
            pbar.update(1)
        else:
            ret = cap.grab()
            if not ret:
                break
            f += 1
            pbar.update(1)
            
    pbar.close()
    cap.release()
    
    if not diffs:
        return 5.0
        
    # Analyze visual frame deviations to find transitions
    mean_val = np.mean(diffs)
    std_val = np.std(diffs)
    # Slide transitions stand out heavily over zoom/pan noise, threshold is set carefully
    threshold = max(mean_val + 2.0 * std_val, 1.5)
    
    peaks = []
    for i in range(1, len(diffs) - 1):
        if diffs[i] > threshold and diffs[i] >= diffs[i-1] and diffs[i] >= diffs[i+1]:
            peaks.append(frame_indices[i])
            
    if len(peaks) < 2:
        print("Auto-detect: Could not find clear transition structures in sample. Defaulting to 5.0s.")
        return 5.0
        
    # Calculate intervals (seconds) with a minimum separation filter
    intervals = []
    min_interval_frames = int(1.0 * fps)
    
    last_peak = peaks[0]
    filtered_peaks = [last_peak]
    for p in peaks[1:]:
        if p - last_peak >= min_interval_frames:
            filtered_peaks.append(p)
            last_peak = p

    for i in range(len(filtered_peaks) - 1):
        gap_frames = filtered_peaks[i+1] - filtered_peaks[i]
        gap_sec = gap_frames / fps
        intervals.append(gap_sec)
            
    if not intervals:
        print("Auto-detect: No valid intervals found. Defaulting to 5.0s.")
        return 5.0
        
    # Round intervals to nearest 0.1s to find the most common display duration
    rounded_intervals = [round(inv, 1) for inv in intervals]
    
    from collections import Counter
    counts = Counter(rounded_intervals)
    most_common, freq = counts.most_common(1)[0]
    
    # Smooth to nearest 0.5s if it's very close (within 0.25s)
    nearest_half = round(most_common * 2) / 2
    if abs(most_common - nearest_half) <= 0.25:
        detected_duration = nearest_half
    else:
        detected_duration = most_common
        
    print(f"Auto-detect: Detected a slide duration of {detected_duration}s (based on {freq} matches).")
    return detected_duration

def extract_slides(video_path, output_dir, duration=None, fps=None):
    """Extracts original slides from video using a robust time-based math calculation."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {video_path}")
        
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    os.makedirs(output_dir, exist_ok=True)
    
    if fps is None or fps <= 0:
        fps = float(cap.get(cv2.CAP_PROP_FPS))
    if fps <= 0:
        fps = 30.0
        
    # Check if duration is specified, otherwise auto-detect it
    if duration is None or duration <= 0:
        print("Duration parameter not specified. Auto-detecting slide duration...")
        duration = auto_detect_slide_duration(video_path, fps)
        print(f"Using auto-detected duration of {duration}s.")
    else:
        print(f"Using specified slide duration of {duration}s.")
        
    # Standard time-based mathematical calculation
    frames_per_slide = int(duration * fps)
    period = frames_per_slide
    
    target_frames = {}
    if period > 0:
        total_slides = int(total_frames // period)
        if total_slides == 0 and total_frames > 0:
            total_slides = 1
        
        print(f"Time-based extraction: Extrapolating {total_slides} slides using period of {duration}s ({frames_per_slide} frames at {fps} FPS)...")
        for i in range(total_slides):
            # Calculate the exact center frame of each slide segment
            center = int(i * period + frames_per_slide / 2)
            if center < total_frames:
                target_frames[center] = i
    else:
        raise ValueError("Calculated slide period cannot be zero or negative.")
        
    if not target_frames:
        print("No target frames scheduled for extraction.")
        cap.release()
        return []
        
    # Pass 2: Seek directly and extract selected frames (massively fast!)
    saved_paths = []
    sorted_targets = sorted(target_frames.items())
    
    pbar = tqdm(total=len(sorted_targets), desc="Exporting images")
    for f_idx, slide_num in sorted_targets:
        cap.set(cv2.CAP_PROP_POS_FRAMES, f_idx)
        ret, frame = cap.read()
        if ret and frame is not None:
            out_path = os.path.join(output_dir, f"extracted_slide_{slide_num:03d}.jpg")
            cropped_frame = crop_black_borders(frame)
            cv2.imwrite(out_path, cropped_frame)
            saved_paths.append(out_path)
        pbar.update(1)
        
    pbar.close()
    cap.release()
    print(f"Extraction completed! {len(saved_paths)} images successfully saved to '{output_dir}'.")
    return saved_paths
