"""
SmartPatientCare - Photorealistic CCTV Demo Video Generator
Author: Gauri (Frontend & CV Lead)

Generates demo CCTV video clips with realistic human figures so YOLO detects
persons with high confidence and triggers explainable temporal rules.
"""

import cv2
import numpy as np
import os
import shutil
import sys

def get_person_assets():
    """Gets person crop from cached bus.jpg or creates synthetic person."""
    bus_path = "bus.jpg"
    if not os.path.exists(bus_path):
        try:
            import urllib.request
            urllib.request.urlretrieve("https://ultralytics.com/images/bus.jpg", bus_path)
        except Exception:
            pass

    if os.path.exists(bus_path):
        img = cv2.imread(bus_path)
        # Person 3 in bus.jpg: [408:860, 223:344]
        person = img[408:860, 223:344]
        return person
    return None

def overlay_person(frame, person_img, cx, cy, target_w, target_h, rotate_angle=0):
    """Overlays person onto frame at (cx, cy) with given size and rotation."""
    if person_img is None:
        return

    resized = cv2.resize(person_img, (target_w, target_h))
    if rotate_angle == 90:
        resized = cv2.rotate(resized, cv2.ROTATE_90_CLOCKWISE)
    elif rotate_angle == 270:
        resized = cv2.rotate(resized, cv2.ROTATE_90_COUNTERCLOCKWISE)

    ph, pw = resized.shape[:2]
    fh, fw = frame.shape[:2]

    x1 = int(cx - pw // 2)
    y1 = int(cy - ph // 2)
    x2 = x1 + pw
    y2 = y1 + ph

    # Clip to frame boundary
    src_x1 = max(0, -x1)
    src_y1 = max(0, -y1)
    src_x2 = pw - max(0, x2 - fw)
    src_y2 = ph - max(0, y2 - fh)

    dst_x1 = max(0, x1)
    dst_y1 = max(0, y1)
    dst_x2 = min(fw, x2)
    dst_y2 = min(fh, y2)

    if dst_x2 > dst_x1 and dst_y2 > dst_y1:
        # Subtle alpha blend at borders
        frame[dst_y1:dst_y2, dst_x1:dst_x2] = resized[src_y1:src_y2, src_x1:src_x2]

def draw_room_background(width, height, room_id, patient_id, camera_id):
    """Draws realistic hospital ward room with bed and monitor."""
    frame = np.full((height, width, 3), (218, 224, 230), dtype=np.uint8)
    floor_y = int(height * 0.65)
    frame[floor_y:height, :] = (170, 175, 180)
    cv2.line(frame, (0, floor_y), (width, floor_y), (130, 135, 140), 2)

    # Bed
    bed_x, bed_y = int(width * 0.18), int(height * 0.20)
    bed_w, bed_h = int(width * 0.58), int(height * 0.48)
    cv2.rectangle(frame, (bed_x, bed_y), (bed_x + bed_w, bed_y + bed_h), (245, 246, 250), -1)
    cv2.rectangle(frame, (bed_x, bed_y), (bed_x + bed_w, bed_y + bed_h), (110, 115, 125), 3)

    # Pillow
    cv2.rectangle(frame, (bed_x + 15, bed_y + 20), (bed_x + 95, bed_y + 85), (225, 230, 238), -1)

    # IV Pole
    pole_x = bed_x + bed_w + 25
    cv2.line(frame, (pole_x, bed_y - 30), (pole_x, floor_y + 20), (140, 140, 145), 3)
    cv2.rectangle(frame, (pole_x - 10, bed_y - 25), (pole_x + 10, bed_y + 20), (200, 230, 245), -1)

    # CCTV Top Header
    cv2.rectangle(frame, (0, 0), (width, 38), (18, 22, 28), -1)
    cv2.circle(frame, (18, 19), 5, (0, 0, 230), -1)
    cv2.putText(frame, f"CCTV DEMO VIDEO | {camera_id} • {room_id} ({patient_id})", (32, 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 1, cv2.LINE_AA)

    return frame, (bed_x, bed_y, bed_w, bed_h)

def generate_video(filename, scenario_type, room_id, patient_id, camera_id, person_asset, duration_sec=12, fps=20):
    width, height = 640, 480
    total_frames = duration_sec * fps
    os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, fps, (width, height))

    for idx in range(total_frames):
        t = idx / fps
        frame, (bx, by, bw, bh) = draw_room_background(width, height, room_id, patient_id, camera_id)
        px = bx + bw // 2
        py = by + bh // 2

        if scenario_type == "fall":
            if t < 3.0:
                # Upright/Sitting in bed
                cx = px
                cy = py
                overlay_person(frame, person_asset, cx, cy, 65, 145, rotate_angle=0)
            elif t < 5.5:
                # Sits on edge of bed
                prog = (t - 3.0) / 2.5
                cx = px + int(prog * 60)
                cy = py + int(prog * 25)
                overlay_person(frame, person_asset, cx, cy, 65, 145, rotate_angle=0)
            elif t < 6.5:
                # Plunges downward rapidly towards floor
                fall_p = (t - 5.5) / 1.0
                cx = px + 60 + int(fall_p * 20)
                cy = (py + 25) + int(fall_p * (360 - (py + 25)))
                rot = 90 if fall_p > 0.4 else 0
                overlay_person(frame, person_asset, cx, cy, 68, 160, rotate_angle=rot)
            else:
                # Fallen on floor (horizontal posture)
                cx = px + 80
                cy = 360
                overlay_person(frame, person_asset, cx, cy, 68, 160, rotate_angle=90)

        elif scenario_type == "left_bed":
            if t < 3.0:
                cx, cy = px, py
                overlay_person(frame, person_asset, cx, cy, 65, 145, rotate_angle=0)
            elif t < 6.5:
                prog = (t - 3.0) / 3.5
                cx = px + int(prog * 220)
                cy = py + int(prog * 80)
                overlay_person(frame, person_asset, cx, cy, 65, 145, rotate_angle=0)
            else:
                cx = px + 220
                cy = py + 80
                overlay_person(frame, person_asset, cx, cy, 65, 145, rotate_angle=0)

        elif scenario_type == "movement":
            # Erratic rapid agitation
            cx = px + int(32 * np.sin(t * 12))
            cy = py + int(22 * np.cos(t * 9))
            overlay_person(frame, person_asset, cx, cy, 65, 145, rotate_angle=0)

        else: # Normal in bed
            cx = px
            cy = py + int(2 * np.sin(t * 2))
            overlay_person(frame, person_asset, cx, cy, 65, 145, rotate_angle=0)

        out.write(frame)

    out.release()
    return filename

def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dirs = [
        os.path.join(root, "demo", "videos"),
        os.path.join(os.path.dirname(root), "..", "frontend", "dashboard", "videos")
    ]

    person_asset = get_person_assets()

    videos = [
        ("room101.mp4", "fall", "ROOM101", "P001", "CAM101"),
        ("room102.mp4", "movement", "ROOM102", "P002", "CAM102"),
        ("room103.mp4", "left_bed", "ROOM103", "P003", "CAM103"),
        ("room104.mp4", "normal", "ROOM104", "P004", "CAM104"),
        ("fall_demo.mp4", "fall", "ROOM101", "P001", "CAM101")
    ]

    print("Generating CCTV demo videos with YOLO-detectable person figures...")
    for filename, scenario, room_id, patient_id, camera_id in videos:
        p1 = os.path.join(target_dirs[0], filename)
        generate_video(p1, scenario, room_id, patient_id, camera_id, person_asset)
        print(f"Generated {p1}")

        p2 = os.path.join(target_dirs[1], filename)
        os.makedirs(os.path.dirname(p2), exist_ok=True)
        shutil.copy2(p1, p2)
        print(f"Copied to {p2}")

    print("All CCTV demo videos generated successfully.")

if __name__ == "__main__":
    main()
