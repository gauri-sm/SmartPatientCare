"""
SmartPatientCare - Synthetic Hospital Bed Video Generator
Author: Gauri (Frontend & CV Lead)

Generates a realistic test video showing the sequence:
1. Normal patient in bed (Phase 1)
2. Erratic motion/agitation (Phase 2)
3. Patient leaving bed (Phase 3)
4. Patient falling to the floor (Phase 4)

Produces an MP4 video that can be fed directly into demo_runner.py.
"""

import cv2
import numpy as np
import os
import sys

def generate_demo_video(
    output_path: str = "demo/sample_patient_bed.mp4",
    width: int = 640,
    height: int = 480,
    fps: int = 20,
    total_seconds: int = 16
) -> str:
    """
    Generates a synthetic bedside video showing normal posture transitioning to fall.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    total_frames = fps * total_seconds
    
    # Coordinates for bed
    bed_x, bed_y = int(width * 0.20), int(height * 0.20)
    bed_w, bed_h = int(width * 0.55), int(height * 0.50)

    # Patient representation coordinates
    px = bed_x + bed_w // 2
    py = bed_y + bed_h // 2
    pw = 90
    ph = 55

    for frame_idx in range(total_frames):
        t = frame_idx / fps
        
        # Hospital room background (subtle blue-gray walls, floor)
        frame = np.full((height, width, 3), (220, 225, 230), dtype=np.uint8)
        
        # Floor area
        floor_y = int(height * 0.65)
        frame[floor_y:height, :] = (180, 185, 190)

        # Bed frame & mattress
        cv2.rectangle(frame, (bed_x, bed_y), (bed_x + bed_w, bed_y + bed_h), (240, 240, 245), -1) # Mattress
        cv2.rectangle(frame, (bed_x, bed_y), (bed_x + bed_w, bed_y + bed_h), (120, 120, 130), 3)  # Frame
        cv2.putText(frame, "HOSPITAL BED 101", (bed_x + 10, bed_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 110), 1)

        # Phase logic:
        # 0 - 4s: Phase 1 (Normal in bed, small breathing oscillation)
        if t < 4.0:
            phase_label = "PHASE 1: Normal Resting in Bed"
            cx = px
            cy = py + int(2 * np.sin(t * 3))
            w_box, h_box = pw, ph

        # 4 - 8s: Phase 2 (Abnormal agitation/erratic movement in bed)
        elif t < 8.0:
            phase_label = "PHASE 2: Erratic Tremor / Agitation"
            cx = px + int(np.random.randint(-18, 18))
            cy = py + int(np.random.randint(-12, 12))
            w_box, h_box = pw + int(np.random.randint(-10, 10)), ph

        # 8 - 12s: Phase 3 (Patient sits up, vacates bed area)
        elif t < 12.0:
            phase_label = "PHASE 3: Patient Vacating Bed"
            progress = (t - 8.0) / 4.0
            cx = int(px + progress * (bed_w * 0.55))
            cy = int(py + progress * 50)
            w_box, h_box = 60, 95 # Upright standing/walking aspect ratio

        # 12 - 16s: Phase 4 (Sudden fall downward onto the floor!)
        else:
            phase_label = "PHASE 4: Sudden Patient Fall"
            fall_progress = min(1.0, (t - 12.0) / 0.8) # Quick fall in 0.8s
            cx = int(px + (bed_w * 0.55) + fall_progress * 20)
            cy = int((py + 50) + fall_progress * 130) # Plunges to floor
            # When fallen, bounding box flattens horizontally
            if fall_progress > 0.6:
                w_box, h_box = 110, 45 # Horizontal flat on ground
            else:
                w_box, h_box = 70, 80

        # Draw patient body figure
        top_left = (max(0, cx - w_box // 2), max(0, cy - h_box // 2))
        bottom_right = (min(width - 1, cx + w_box // 2), min(height - 1, cy + h_box // 2))
        
        # Patient body (hospital teal gown)
        cv2.rectangle(frame, top_left, bottom_right, (160, 140, 60), -1)
        cv2.rectangle(frame, top_left, bottom_right, (100, 80, 20), 2)
        
        # Patient head
        head_radius = 16
        head_center = (cx, max(head_radius, top_left[1] - head_radius + 4))
        cv2.circle(frame, head_center, head_radius, (190, 200, 230), -1)
        cv2.circle(frame, head_center, head_radius, (120, 130, 160), 2)

        # Simulation Phase Banner
        cv2.putText(frame, phase_label, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (40, 40, 180), 2)
        cv2.putText(frame, f"Time: {t:.1f}s / {total_seconds}s", (20, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (80, 80, 80), 1)

        out.write(frame)

    out.release()
    return output_path

if __name__ == "__main__":
    out_file = generate_demo_video()
    print(f"Generated demo video: {out_file}")
