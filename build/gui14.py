import subprocess, sys, threading, time, os, logging, signal, platform
from pathlib import Path
from tkinter import Tk, Canvas, PhotoImage
from PIL import Image, ImageTk, ImageDraw
import pandas as pd
from datetime import datetime
from picamera2 import Picamera2  # Using Picamera2 for Arducam

# ===== Load Config =====
def load_config(file):
    return {k.strip(): v.strip() for k, v in (line.split("=", 1) for line in open(file) if "=" in line)}

BASE = Path(__file__).parent
cfg = load_config(BASE / "config.txt")

ASSETS_PATH = Path(cfg["ASSETS_PATH"])
DATA_FILE = Path(cfg["DATA_FILE"])
STABLE_LOG_FILE = Path(cfg["STABLE_LOG_FILE"])
SERIAL_INPUT_FILE = Path(cfg["SERIAL_INPUT_FILE"])
STABILITY_LOG_FILE = BASE / cfg["STABILITY_LOG_FILE"]
IMG_CSV = BASE / cfg["IMAGE_CONFIG"]
TXT_CSV = BASE / cfg["TEXT_CONFIG"]
SCRIPT = Path(cfg["INTERRUPT_SCRIPT"])
LOG_FILE = BASE / cfg["LOG_FILE"]
DEVICE_NAME = cfg.get("DEVICE_NAME", "OptiA1")
UPLOAD_SCRIPT = BASE / "fileupload.py"

SAVE_FOLDER = BASE / "saved"
TEMP_FOLDER = BASE / "temp"
SAVE_FOLDER.mkdir(exist_ok=True)
TEMP_FOLDER.mkdir(exist_ok=True)

SERIAL_SENDER_SCRIPT = BASE / "serial_file_sender.py"

# ===== Logging =====
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ===== Load CSVs =====
images = pd.read_csv(IMG_CSV).to_dict(orient="records")
texts = pd.read_csv(TXT_CSV).to_dict(orient="records")
rel_asset = lambda p: ASSETS_PATH / p

# ===== GUI Setup =====
win = Tk()
win.attributes('-fullscreen', True)  # Force full-screen mode
win.attributes('-topmost', True)  # Keep window on top of all applications
win.configure(bg="#F5F5F3")

# Get screen dimensions to set canvas size
screen_width = win.winfo_screenwidth()
screen_height = win.winfo_screenheight()
cv = Canvas(win, bg="#F5F5F3", height=screen_height, width=screen_width, bd=0, highlightthickness=0)
cv.place(x=0, y=0)

# Keep references to avoid garbage collection
img_refs, img_ids = {}, {}
for r in images:
    img = PhotoImage(file=rel_asset(r["file_name"]))
    img_refs[r["variable_name"]] = img
    img_ids[r["variable_name"]] = cv.create_image(r["x_pos"] * screen_width / 1920, r["y_pos"] * screen_height / 1080, image=img)
if "interrupt_light" in img_ids:
    cv.itemconfigure(img_ids["interrupt_light"], state="hidden")

txt_ids = {}
for t in texts:
    txt_ids[t["key"]] = cv.create_text(t["x_pos"] * screen_width / 1920, t["y_pos"] * screen_height / 1080, anchor="nw", text=t["text"],
                                       fill=t["color"], font=(t["font_name"], int(t["font_size"] * min(screen_width / 1920, screen_height / 1080))))

# Hide systemstat, placehand, and scanrdy initially if they exist
for img_name in ["systemstat", "placehand", "scanrdy"]:
    if img_name in img_ids:
        cv.itemconfigure(img_ids[img_name], state="normal")

# ===== Camera Setup =====
ROTATE_RIGHT_90 = True
RADIUS = 50

# Get positions and dimensions from camera pane images
left_pane_info = next((item for item in images if item["variable_name"] == "left_camera_pane"), None)
right_pane_info = next((item for item in images if item["variable_name"] == "right_camera_pane"), None)

# Load camera pane images to get their exact dimensions
left_pane_img = Image.open(rel_asset("leftcamerapane.png"))
right_pane_img = Image.open(rel_asset("rightcamerapane.png"))

LEFT_PANE_W, LEFT_PANE_H = left_pane_img.size
RIGHT_PANE_W, RIGHT_PANE_H = right_pane_img.size

# Scale positions for different screen resolutions
if left_pane_info:
    left_video_id = cv.create_image(left_pane_info["x_pos"] * screen_width / 1920, left_pane_info["y_pos"] * screen_height / 1080, image=None)
else:
    left_video_id = cv.create_image(491 * screen_width / 1920, 562 * screen_height / 1080, image=None)  # Fallback

right_id = None
latest_frame = None
captured_path = None
prev_flag = None
last_mtime = None

# Create masks that match the exact size and shape of camera panes
left_mask = Image.new("L", (LEFT_PANE_W, LEFT_PANE_H), 0)
right_mask = Image.new("L", (RIGHT_PANE_W, RIGHT_PANE_H), 0)

# Create rounded rectangle masks matching the camera pane shapes
ImageDraw.Draw(left_mask).rounded_rectangle((0, 0, LEFT_PANE_W, LEFT_PANE_H), RADIUS, fill=255)
ImageDraw.Draw(right_mask).rounded_rectangle((0, 0, RIGHT_PANE_W, RIGHT_PANE_H), RADIUS, fill=255)

# Picamera2 setup
picam2 = None
camera_ready = False

def init_cam():
    global picam2, camera_ready
    try:
        picam2 = Picamera2()
        config = picam2.create_preview_configuration(main={"size": (LEFT_PANE_W, LEFT_PANE_H), "format": "RGB888"})
        picam2.configure(config)
        picam2.start()
        camera_ready = True
        logging.info("CSI camera initialized (Picamera2, RGB888)")
    except Exception as e:
        logging.error(f"Camera init failed: {e}")
        camera_ready = False

def capture_frame():
    global latest_frame
    if not camera_ready:
        return False
    try:
        frame = picam2.capture_array()
        pil_im = Image.fromarray(frame)  # Picamera2 outputs RGB888, no BGR2RGB conversion needed
        if ROTATE_RIGHT_90:
            pil_im = pil_im.rotate(-90, expand=True)
        if pil_im.size != (LEFT_PANE_W, LEFT_PANE_H):
            pil_im = pil_im.resize((LEFT_PANE_W, LEFT_PANE_H), Image.Resampling.LANCZOS)
        latest_frame = pil_im
        return True
    except Exception as e:
        logging.error(f"Frame capture failed: {e}")
        return False

def update_cam():
    if camera_ready and capture_frame():
        img_copy = latest_frame.copy()
        img_copy.putalpha(left_mask)
        imgtk = ImageTk.PhotoImage(image=img_copy)
        cv.itemconfig(left_video_id, image=imgtk)
        img_refs["video_feed"] = imgtk
    win.after(15, update_cam)

# ===== Time Update =====
def update_time():
    if "TIME_TEXT" in txt_ids:
        cv.itemconfig(txt_ids["TIME_TEXT"], text=datetime.now().strftime("%H:%M"))
    win.after(1000, update_time)

# ===== Stable Weight Reader =====
def last_stable_weight():
    try:
        if not STABLE_LOG_FILE.exists(): return None
        lines = [l.strip() for l in open(STABLE_LOG_FILE) if l.strip()]
        if lines and "Stable weight:" in lines[-1]:
            return lines[-1].split("Stable weight:")[1].strip().replace("kg", "").strip()
    except Exception as e:
        logging.error(f"Read stable weight error: {e}")
    return None

def send_data_to_serial(data):
    try:
        with open(SERIAL_INPUT_FILE, 'w') as f:
            f.write(data.strip())
    except Exception as e:
        print("failed to write to serial input file")

stability_weights = []

def monitor_stable_log():
    global last_mtime, captured_path, right_id, stability_weights
    try:
        if STABLE_LOG_FILE.exists():
            m = os.path.getmtime(STABLE_LOG_FILE)
            if last_mtime is None: last_mtime = m
            elif m > last_mtime:
                last_mtime = m
                w = last_stable_weight()
                if w and captured_path and captured_path.exists():
                    safe_w = w.replace(".", "x")
                    ts = captured_path.stem.split(f"{DEVICE_NAME}_")[1]
                    final = SAVE_FOLDER / f"{DEVICE_NAME}_{ts}_{safe_w}.jpg"
                    Image.open(captured_path).save(final)
                    captured_path.unlink()
                    logging.info(f"Event 2: Stable weight detected, saved {final}")

                    with open(STABILITY_LOG_FILE, "a") as f:
                        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: " +
                                ", ".join(f"{val:.2f}" for val in stability_weights) +
                                f" -- stable (final: {w} kg)\n")
                    stability_weights.clear()
                    captured_path = None
                    if right_id:
                        cv.delete(right_id)
                        right_id = None
                        cv.itemconfigure(img_ids["right_camera_pane"], state="normal")
                        img_refs["captured_right"] = None
                        send_data_to_serial("s")
                    
                    # Show systemstat, placehand, and scanrdy again after image is saved
                    for img_name in ["systemstat", "placehand", "scanrdy"]:
                        if img_name in img_ids:
                            cv.itemconfigure(img_ids[img_name], state="normal")
    except Exception as e:
        logging.error(f"Stable log monitor error: {e}")
    win.after(200, monitor_stable_log)

# ===== File Monitoring =====
def monitor_file():
    global captured_path, prev_flag, right_id, stability_weights
    try:
        if camera_ready and DATA_FILE.exists():
            flag, weight = open(DATA_FILE).read().strip().split(",", 1)
            flag, w_val = int(flag), weight.strip().replace(" kg", "")
            try: wf = float(w_val)
            except: wf = 0.0
            disp = f"{wf*1000:.1f} g" if wf < 1 else f"{wf:.2f} kg"
            if "WEIGHT_TEXT" in txt_ids: cv.itemconfig(txt_ids["WEIGHT_TEXT"], text=disp)
            if flag == 1: stability_weights.append(wf)
            if prev_flag == 0 and flag == 1:
                logging.info("Event 1: Interrupt 0→1 detected, preparing to capture image")
                send_data_to_serial("y")
                if "interrupt_light" in img_ids: cv.itemconfigure(img_ids["interrupt_light"], state="normal")
                
                # Hide systemstat, placehand, and scanrdy when interrupt light appears
                for img_name in ["systemstat", "placehand", "scanrdy"]:
                    if img_name in img_ids:
                        cv.itemconfigure(img_ids[img_name], state="hidden")

                def delayed_capture():
                    global captured_path, right_id
                    if capture_frame():
                        ts = datetime.now().strftime("%H-%M-%S_%Y-%m-%d")
                        captured_path = TEMP_FOLDER / f"{DEVICE_NAME}_{ts}.jpg"
                        latest_frame.save(captured_path)
                        
                        img_copy = latest_frame.copy()
                        if img_copy.size != (RIGHT_PANE_W, RIGHT_PANE_H):
                            img_copy = img_copy.resize((RIGHT_PANE_W, RIGHT_PANE_H), Image.Resampling.LANCZOS)
                        img_copy.putalpha(right_mask)
                        
                        imgtk = ImageTk.PhotoImage(image=img_copy)
                        
                        if right_pane_info:
                            right_id = cv.create_image(right_pane_info["x_pos"] * screen_width / 1920, right_pane_info["y_pos"] * screen_height / 1080, image=imgtk)
                        else:
                            right_id = cv.create_image(1427.85693359375 * screen_width / 1920, 562 * screen_height / 1080, image=imgtk)
                            
                        cv.itemconfigure(img_ids["right_camera_pane"], state="hidden")
                        img_refs["captured_right"] = imgtk
                    win.after(5000, lambda: cv.itemconfigure(img_ids["interrupt_light"], state="hidden"))
                    send_data_to_serial("z")

                win.after(1000, delayed_capture)
            prev_flag = flag if prev_flag is not None else flag
    except Exception as e:
        logging.error(f"File monitor error: {e}")
    win.after(200, monitor_file)

# ===== Subprocess Handling =====
subproc_handle = None
serial_handle = None
upload_handle = None

def run_script():
    global subproc_handle, serial_handle, upload_handle
    try:
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP if platform.system() == "Windows" else 0
        start_new_session = None if platform.system() == "Windows" else True
        
        subproc_handle = subprocess.Popen([sys.executable, str(SCRIPT)], creationflags=creation_flags, start_new_session=start_new_session)
        logging.info("Interrupt script started")
        
        serial_handle = subprocess.Popen([sys.executable, str(SERIAL_SENDER_SCRIPT)], creationflags=creation_flags, start_new_session=start_new_session)
        logging.info("Serial file sender started")
        
        upload_handle = subprocess.Popen([sys.executable, str(UPLOAD_SCRIPT)], creationflags=creation_flags, start_new_session=start_new_session)
        logging.info("File upload service started")
    except Exception as e:
        logging.error(f"Start script error: {e}")

def start_when_ready():
    if camera_ready: run_script(); monitor_file()
    else: win.after(100, start_when_ready)

# ===== Close Handling =====
def on_close():
    try:
        if picam2:
            picam2.stop()
    except:
        pass
    
    for handle in [subproc_handle, serial_handle, upload_handle]:
        if handle and handle.poll() is None:
            try:
                if platform.system() == "Windows":
                    handle.send_signal(signal.CTRL_BREAK_EVENT)
                    time.sleep(0.5)
                    handle.terminate()
                else:
                    os.killpg(os.getpgid(handle.pid), signal.SIGTERM)
                logging.info("Subprocess terminated")
            except Exception as e:
                logging.error(f"Error terminating subprocess: {e}")
    win.destroy()

# ===== Initialize =====
threading.Thread(target=init_cam, daemon=True).start()
threading.Thread(target=monitor_stable_log, daemon=True).start()
update_cam()
update_time()
win.after(100, start_when_ready)

win.protocol("WM_DELETE_WINDOW", on_close)
win.resizable(False, False)
win.mainloop()