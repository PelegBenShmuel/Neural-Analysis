import cv2
import numpy as np
from pathlib import Path
from tqdm import tqdm


def run_video_movement(video_folder, rat_id, output_folder, hours_to_analyze=None, fps=25):
    """Extract per-frame movement counts from video segments using MOG2 background subtraction.

    Algorithm: grayscale -> MOG2 background subtraction (history=300, varThreshold=10,
    learningRate=0.3) -> count foreground pixels per frame.

    Supports two video layouts:
    - Hourly segments: rat_segment_000.mp4, rat_segment_001.mp4, ...
    - Single combined file: any *.mp4 in video_folder (processes hour by hour via frame seeking)
    """
    video_folder = Path(video_folder)
    output_folder = Path(output_folder)
    output_path = output_folder / f"{rat_id}_VideoMovement.npy"

    available_segments = sorted(video_folder.glob("rat_segment_*.mp4"))
    use_combined = len(available_segments) == 0

    if use_combined:
        combined_files = sorted(video_folder.glob("*.mp4"))
        if not combined_files:
            raise FileNotFoundError(f"[Video Movement] No video files found in {video_folder}")
        combined_path = combined_files[0]
        cap_probe = cv2.VideoCapture(str(combined_path))
        total_frames_combined = int(cap_probe.get(cv2.CAP_PROP_FRAME_COUNT))
        cap_probe.release()
        total_video_hours = total_frames_combined // (fps * 3600)
        if hours_to_analyze is None:
            hours_to_analyze = total_video_hours
        print(f"[Video Movement] Combined video: {combined_path.name} "
              f"({total_frames_combined} frames, {total_video_hours}h available)")
    else:
        if hours_to_analyze is None:
            hours_to_analyze = len(available_segments)

    if output_path.exists():
        existing = np.load(output_path)
        existing_hours = len(existing) / fps / 3600
        if existing_hours >= hours_to_analyze:
            print(f"[Video Movement] Already exists ({existing_hours:.2f}h), skipping: {output_path}")
            return output_path
        print(f"[Video Movement] Existing file covers {existing_hours:.2f}h but {hours_to_analyze}h requested — reprocessing.")

    print(f"[Video Movement] Processing {hours_to_analyze} hour(s) from {video_folder}")

    all_movement = []

    for hour in range(hours_to_analyze):
        if use_combined:
            cap = cv2.VideoCapture(str(combined_path))
            start_frame = hour * fps * 3600
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            n_frames = fps * 3600
            desc = f"  Hour {hour} ({combined_path.name} @frame {start_frame})"
        else:
            seg_path = video_folder / f"rat_segment_{hour:03d}.mp4"
            if not seg_path.exists():
                print(f"  [WARNING] {seg_path.name} not found — filling hour {hour} with zeros")
                all_movement.append(np.zeros(fps * 3600, dtype=np.float32))
                continue
            cap = cv2.VideoCapture(str(seg_path))
            n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            desc = f"  Hour {hour} ({seg_path.name})"

        bg_sub = cv2.createBackgroundSubtractorMOG2(
            history=300, varThreshold=10, detectShadows=False
        )
        movement = np.zeros(n_frames, dtype=np.float32)

        for i in tqdm(range(n_frames), desc=desc, unit="fr", leave=True):
            ret, frame = cap.read()
            if not ret:
                movement = movement[:i]
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            fg_mask = bg_sub.apply(gray, learningRate=0.3)
            movement[i] = np.count_nonzero(fg_mask)

        cap.release()
        all_movement.append(movement)
        print(f"  Hour {hour} done — mean movement: {movement.mean():.0f} px/frame")

    movement_all = np.concatenate(all_movement)
    np.save(output_path, movement_all)
    print(f"[Video Movement] Saved {len(movement_all)} frames ({len(movement_all)/fps/3600:.2f}h) -> {output_path}")

    return output_path
