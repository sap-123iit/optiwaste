import subprocess
import sys
from pathlib import Path
from tkinter import Tk, Canvas, PhotoImage
import threading
import cv2
from PIL import Image, ImageTk, ImageDraw
import time
import os
from datetime import datetime

# ====== Config Values ======
ASSETS_PATH = Path(r"E:\Forgevision\Optiwaste\Device\optiwaste\build\assets\frame0")
DATA_FILE = Path(r"E:\Forgevision\Optiwaste\Device\optiwaste\build\final_weight_interrupt.txt")
STABLE_LOG_FILE = Path(r"E:\Forgevision\Optiwaste\Device\optiwaste\build\stable_weight_log.txt")
SAVE_FOLDER = Path(__file__).parent / "saved"
TEMP_FOLDER = Path(__file__).parent / "temp"  # Create temp_images in script's directory
SAVE_FOLDER.mkdir(exist_ok=True)
TEMP_FOLDER.mkdir(exist_ok=True)

# ====== Image & Text Config ======
image_configs = [
    {"variable_name": "right_canvas", "file_name": "rightcanvas.png", "x_pos": 748.0, "y_pos": 300.0},
    {"variable_name": "left_canvas", "file_name": "leftcanvas.png", "x_pos": 258.0, "y_pos": 293.0},
    {"variable_name": "interrupt_light", "file_name": "interruptlight.png", "x_pos": 262.0, "y_pos": 297.0},
    {"variable_name": "left_camera_pane", "file_name": "leftcamerapane.png", "x_pos": 262.0, "y_pos": 298.0},
    {"variable_name": "right_camera_pane", "file_name": "rightcamerapane.png", "x_pos": 754.0, "y_pos": 297.0},
    {"variable_name": "left_camera_heading", "file_name": "leftcameraheading.png", "x_pos": 124.0, "y_pos": 98.0},
    {"variable_name": "right_camera_heading", "file_name": "rightcameraheading.png", "x_pos": 641.0, "y_pos": 98.0},
    {"variable_name": "network_wifi", "file_name": "network_wifi.png", "x_pos": 969.0, "y_pos": 35.0},
    {"variable_name": "place_hand", "file_name": "placehand.png", "x_pos": 75.0, "y_pos": 544.0},
    {"variable_name": "optiwaste_logo", "file_name": "optiwastelogo.png", "x_pos": 166.0, "y_pos": 39.0}
]

text_configs = [
    {"key": "WEIGHT_TEXT", "text": "0.00 kg", "x_pos": 824.0, "y_pos": 495.0, "color": "#155E24", "font": ("Inter Bold", -40)},
    {"key": "TIME_TEXT", "text": "00:00", "x_pos": 805.0, "y_pos": 13.0, "color": "#727272", "font": ("Inter Bold", -40)},
    {"key": "STATUS_LABEL_TEXT", "text": "System status", "x_pos": 55.0, "y_pos": 495.0, "color": "#06552A", "font": ("Inter Bold", -20)},
    {"key": "STATUS_TEXT", "text": "Ready to Scan", "x_pos": 87.0, "y_pos": 533.0, "color": "#727272", "font": ("Inter Bold", -20)}
]

def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)

# ====== Tkinter Setup ======
window = Tk()
window.geometry("1023x600")
window.configure(bg="#F5F5F3")

canvas = Canvas(window, bg="#F5F5F3", height=600, width=1023, bd=0, highlightthickness=0, relief="ridge")
canvas.place(x=0, y=0)

image_refs = {}
image_ids = {}
for img_data in image_configs:
    img = PhotoImage(file=relative_to_assets(img_data["file_name"]))
    img_id = canvas.create_image(img_data["x_pos"], img_data["y_pos"], image=img)
    image_refs[img_data["variable_name"]] = img
    image_ids[img_data["variable_name"]] = img_id

canvas.itemconfigure(image_ids["interrupt_light"], state="hidden")

text_ids = {}
for text_data in text_configs:
    tid = canvas.create_text(
        text_data["x_pos"],
        text_data["y_pos"],
        anchor="nw",
        text=text_data["text"],
        fill=text_data["color"],
        font=text_data["font"]
    )
    text_ids[text_data["key"]] = tid

# ====== Camera ======
cap = None
camera_ready = False
PREVIEW_WIDTH = 410
PREVIEW_HEIGHT = 240
PREVIEW_X = 262.0
PREVIEW_Y = 298.0
CORNER_RADIUS = 25

left_video_id = canvas.create_image(PREVIEW_X, PREVIEW_Y, image=None)
right_captured_id = None  # Track the captured image on right pane
latest_frame_pil = None
captured_image_path = None
prev_interrupt_flag = None  # None so first run doesn't trigger save
last_mtime = None  # Track last modification time of stable_weight_log.txt

def create_rounded_mask(w, h, r):
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, w, h), r, fill=255)
    return mask

mask = create_rounded_mask(PREVIEW_WIDTH, PREVIEW_HEIGHT, CORNER_RADIUS)

def initialize_camera():
    global cap, camera_ready
    for attempt in range(3):  # Retry up to 3 times
        try:
            cap = cv2.VideoCapture(0)
            cap.set(cv2.CAP_PROP_FPS, 30)
            if cap.isOpened():
                camera_ready = True
                print(f"Camera initialized successfully on attempt {attempt + 1}")
                return
            else:
                cap.release()
        except Exception as e:
            print(f"Camera initialization attempt {attempt + 1} failed: {e}")
        time.sleep(1)  # Wait before retrying
    print("Failed to initialize camera after 3 attempts")
    camera_ready = False

def capture_frame_with_retry(max_attempts=3, delay=0.1):
    """Attempt to capture a valid frame with retries."""
    global latest_frame_pil
    for attempt in range(max_attempts):
        ret, frame = cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (PREVIEW_WIDTH, PREVIEW_HEIGHT))
            latest_frame_pil = Image.fromarray(frame)
            return True
        else:
            print(f"Frame capture attempt {attempt + 1} failed")
            time.sleep(delay)
    print("Failed to capture frame after retries")
    latest_frame_pil = None
    return False

def update_camera():
    global latest_frame_pil
    if not camera_ready:
        window.after(100, update_camera)
        return

    if capture_frame_with_retry():
        img_pil = latest_frame_pil.copy()
        img_pil.putalpha(mask)
        imgtk = ImageTk.PhotoImage(image=img_pil)
        canvas.itemconfig(left_video_id, image=imgtk)
        image_refs["video_feed"] = imgtk
    else:
        print("Failed to update video feed")

    window.after(15, update_camera)

# ====== Time ======
def update_time():
    now = datetime.now().strftime("%H:%M")
    canvas.itemconfig(text_ids["TIME_TEXT"], text=now)
    window.after(1000, update_time)

# ====== Stable Weight Reader ======
def get_last_stable_weight():
    if not STABLE_LOG_FILE.exists():
        print(f"Stable weight log file not found: {STABLE_LOG_FILE}")
        return None
    with open(STABLE_LOG_FILE, "r") as f:
        lines = [line.strip() for line in f if line.strip()]
    if not lines:
        print("Stable weight log file is empty")
        return None
    last_line = lines[-1]
    if "Stable weight:" in last_line:
        weight_str = last_line.split("Stable weight:")[1].strip()
        # Remove unit if present
        if weight_str.endswith("kg"):
            weight_str = weight_str.replace("kg", "").strip()
        print(f"Retrieved stable weight: {weight_str}")
        return weight_str
    print(f"Invalid stable weight format in log: {last_line}")
    return None

# ====== Monitor Stable Weight Log ======
def monitor_stable_weight_log():
    global last_mtime, captured_image_path, right_captured_id

    try:
        if STABLE_LOG_FILE.exists():
            current_mtime = os.path.getmtime(STABLE_LOG_FILE)
            global last_mtime
            if last_mtime is None:
                last_mtime = current_mtime  # Initialize on first check
            elif current_mtime > last_mtime:
                # New data detected in stable_weight_log.txt
                last_mtime = current_mtime
                stable_weight = get_last_stable_weight()
                if stable_weight and captured_image_path and captured_image_path.exists():
                    # Format weight as string, removing unit and replacing decimal with 'x'
                    safe_weight = stable_weight.replace(".", "x").strip()
                    ts = captured_image_path.stem.split("OptiA1_")[1]  # Extract timestamp from temp filename
                    final_filename = SAVE_FOLDER / f"OptiA1_{ts}_{safe_weight}.jpg"
                    # Move image by saving and deleting
                    Image.open(captured_image_path).save(final_filename)
                    captured_image_path.unlink()  # Delete temp image
                    print(f"Image saved to: {final_filename} and deleted from: {captured_image_path}")
                    captured_image_path = None  # Reset
                    # Restore right pane to rightcamerapane.png
                    if right_captured_id:
                        canvas.delete(right_captured_id)  # Remove captured image
                        right_captured_id = None
                        canvas.itemconfigure(image_ids["right_camera_pane"], state="normal")
                        image_refs["captured_right"] = None
                else:
                    if not stable_weight:
                        print("No stable weight available for saving")
                    if not captured_image_path or not captured_image_path.exists():
                        print(f"No captured image available or file not found: {captured_image_path}")
        else:
            print(f"Stable weight log file not found: {STABLE_LOG_FILE}")

    except Exception as e:
        print(f"Stable weight log monitor error: {e}")

    window.after(200, monitor_stable_weight_log)

# ====== Monitor File ======
def monitor_file():
    global captured_image_path, prev_interrupt_flag, right_captured_id

    try:
        if not camera_ready:
            return  # Skip if camera is not ready

        if DATA_FILE.exists():
            with open(DATA_FILE, "r") as f:
                line = f.read().strip()
                if "," in line:
                    flag_str, weight_str = line.split(",", 1)
                    interrupt_flag = int(flag_str)
                    weight_val = weight_str.strip().replace(" kg", "")

                    try:
                        weight_float = float(weight_val)
                    except ValueError:
                        weight_float = 0.0
                        print(f"Invalid weight value in DATA_FILE: {weight_val}")

                    if weight_float < 1.0:
                        display_weight = f"{weight_float*1000:.1f} g"
                    else:
                        display_weight = f"{weight_float:.2f} kg"

                    canvas.itemconfig(text_ids["WEIGHT_TEXT"], text=display_weight)

                    # EVENT: 0 → 1  (Capture image, save to temp_images & show right pane)
                    if prev_interrupt_flag == 0 and interrupt_flag == 1:
                        canvas.itemconfigure(image_ids["interrupt_light"], state="normal")
                        if capture_frame_with_retry():
                            ts = datetime.now().strftime("%H-%M-%S_%Y-%m-%d")
                            temp_filename = TEMP_FOLDER / f"OptiA1_{ts}.jpg"
                            latest_frame_pil.save(temp_filename)
                            captured_image_path = temp_filename
                            img_copy = latest_frame_pil.copy()
                            img_copy.putalpha(mask)
                            imgtk = ImageTk.PhotoImage(image=img_copy)
                            right_captured_id = canvas.create_image(754.0, 297.0, image=imgtk)
                            image_refs["captured_right"] = imgtk
                            print(f"Image captured and saved to: {temp_filename}")
                        else:
                            print("No latest frame available to capture")
                        window.after(5000, lambda: canvas.itemconfigure(image_ids["interrupt_light"], state="hidden"))

                    prev_interrupt_flag = interrupt_flag if prev_interrupt_flag is not None else interrupt_flag
        else:
            print(f"Data file not found: {DATA_FILE}")

    except Exception as e:
        print(f"File monitor error: {e}")

    window.after(200, monitor_file)

# ====== Subprocess ======
subproc_handle = None
def run_interrupt_script():
    global subproc_handle
    try:
        subproc_handle = subprocess.Popen([sys.executable, r"E:\Forgevision\Optiwaste\Device\optiwaste\build\interrupt_weightread_stability.py"])
        print("Interrupt script started")
    except Exception as e:
        print(f"Error starting interrupt script: {e}")

threading.Thread(target=run_interrupt_script, daemon=True).start()

# ====== Start ======
def start_monitor_file():
    if camera_ready:
        monitor_file()
    else:
        window.after(100, start_monitor_file)  # Check again after 100ms

threading.Thread(target=initialize_camera, daemon=True).start()
threading.Thread(target=monitor_stable_weight_log, daemon=True).start()
update_camera()
update_time()
start_monitor_file()

# ====== Close ======
def on_close():
    global cap, subproc_handle
    if cap:
        cap.release()
    if subproc_handle and subproc_handle.poll() is None:
        subproc_handle.terminate()
    window.destroy()

window.protocol("WM_DELETE_WINDOW", on_close)
window.resizable(False, False)
window.mainloop()