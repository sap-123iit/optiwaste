import subprocess, sys, threading, cv2, time, os, logging, signal, platform
from pathlib import Path
from tkinter import Tk, Canvas, PhotoImage
from PIL import Image, ImageTk, ImageDraw
import pandas as pd
from datetime import datetime

# ===== Load Config =====
def load_config(file):
    return {k.strip(): v.strip() for k, v in (line.split("=", 1) for line in open(file) if "=" in line)}

BASE = Path(__file__).parent
cfg = load_config(BASE / "config.txt")

ASSETS_PATH, DATA_FILE, STABLE_LOG_FILE = Path(cfg["ASSETS_PATH"]), Path(cfg["DATA_FILE"]), Path(cfg["STABLE_LOG_FILE"])
STABILITY_LOG_FILE = BASE / cfg["STABILITY_LOG_FILE"]
IMG_CSV, TXT_CSV, SCRIPT, LOG_FILE = BASE / cfg["IMAGE_CONFIG"], BASE / cfg["TEXT_CONFIG"], Path(cfg["INTERRUPT_SCRIPT"]), BASE / cfg["LOG_FILE"]
SAVE_FOLDER, TEMP_FOLDER = BASE / "saved", BASE / "temp"
SAVE_FOLDER.mkdir(exist_ok=True), TEMP_FOLDER.mkdir(exist_ok=True)

# ===== Logging =====
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ===== Load CSVs =====
images = pd.read_csv(IMG_CSV).to_dict(orient="records")
texts = pd.read_csv(TXT_CSV).to_dict(orient="records")
rel_asset = lambda p: ASSETS_PATH / p

# ===== GUI Setup =====
win = Tk(); win.geometry("1023x600"); win.configure(bg="#F5F5F3")
cv = Canvas(win, bg="#F5F5F3", height=600, width=1023, bd=0, highlightthickness=0); cv.place(x=0, y=0)

# Keep references to avoid Tkinter image garbage collection
img_refs, img_ids = {}, {}
for r in images:
    img = PhotoImage(file=rel_asset(r["file_name"]))
    img_refs[r["variable_name"]] = img
    img_ids[r["variable_name"]] = cv.create_image(r["x_pos"], r["y_pos"], image=img)
if "interrupt_light" in img_ids:
    cv.itemconfigure(img_ids["interrupt_light"], state="hidden")

txt_ids = {t["key"]: cv.create_text(t["x_pos"], t["y_pos"], anchor="nw", text=t["text"], fill=t["color"],
            font=(t["font_name"], t["font_size"])) for t in texts}

# ===== Camera =====
cap, camera_ready, PREVIEW_W, PREVIEW_H, PREVIEW_X, PREVIEW_Y, RADIUS = None, False, 410, 240, 262.0, 298.0, 25
left_video_id, right_id, latest_frame, captured_path, prev_flag, last_mtime = cv.create_image(PREVIEW_X, PREVIEW_Y, image=None), None, None, None, None, None
mask = Image.new("L", (PREVIEW_W, PREVIEW_H), 0); ImageDraw.Draw(mask).rounded_rectangle((0,0,PREVIEW_W,PREVIEW_H), RADIUS, fill=255)

def init_cam():
    global cap, camera_ready
    for a in range(3):
        try:
            cap = cv2.VideoCapture(0); cap.set(cv2.CAP_PROP_FPS, 30)
            if cap.isOpened(): camera_ready = True; logging.info(f"Camera OK on try {a+1}"); return
            cap.release()
        except Exception as e: logging.error(f"Cam init fail {a+1}: {e}")
        time.sleep(1)
    logging.error("Camera failed after 3 tries")

def capture_frame():
    global latest_frame
    for _ in range(3):
        ret, frame = cap.read()
        if ret:
            latest_frame = Image.fromarray(cv2.cvtColor(cv2.resize(frame, (PREVIEW_W, PREVIEW_H)), cv2.COLOR_BGR2RGB))
            return True
        time.sleep(0.1)
    latest_frame = None; logging.error("Frame capture failed"); return False

def update_cam():
    if camera_ready and capture_frame():
        img_copy = latest_frame.copy(); img_copy.putalpha(mask)
        imgtk = ImageTk.PhotoImage(image=img_copy)
        cv.itemconfig(left_video_id, image=imgtk); img_refs["video_feed"] = imgtk
    win.after(15, update_cam)

# ===== Time =====
def update_time(): 
    if "TIME_TEXT" in txt_ids: cv.itemconfig(txt_ids["TIME_TEXT"], text=datetime.now().strftime("%H:%M"))
    win.after(1000, update_time)

# ===== Weight Log Reader =====
def last_stable_weight():
    try:
        if not STABLE_LOG_FILE.exists(): return None
        lines = [l.strip() for l in open(STABLE_LOG_FILE) if l.strip()]
        if lines and "Stable weight:" in lines[-1]:
            return lines[-1].split("Stable weight:")[1].strip().replace("kg", "").strip()
    except Exception as e: logging.error(f"Read stable weight error: {e}")
    return None

# Track weights for stability log
stability_weights = []

# ===== Event 2: Stability Achieved =====
def monitor_stable_log():
    global last_mtime, captured_path, right_id, stability_weights
    try:
        if STABLE_LOG_FILE.exists():
            m = os.path.getmtime(STABLE_LOG_FILE)
            if last_mtime is None:
                last_mtime = m
            elif m > last_mtime:
                last_mtime = m
                w = last_stable_weight()
                if w and captured_path and captured_path.exists():
                    safe_w, ts = w.replace(".", "x"), captured_path.stem.split("OptiA1_")[1]
                    final = SAVE_FOLDER / f"OptiA1_{ts}_{safe_w}.jpg"
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
                        cv.delete(right_id); right_id = None
                        cv.itemconfigure(img_ids["right_camera_pane"], state="normal")
                        img_refs["captured_right"] = None
    except Exception as e: logging.error(f"Stable log monitor: {e}")
    win.after(200, monitor_stable_log)

# ===== Event 1: Interrupt 0→1 =====
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

            if flag == 1:
                stability_weights.append(wf)

            if prev_flag == 0 and flag == 1:
                logging.info("Event 1: Interrupt 0→1 detected, capturing image")
                if "interrupt_light" in img_ids: cv.itemconfigure(img_ids["interrupt_light"], state="normal")
                if capture_frame():
                    ts = datetime.now().strftime("%H-%M-%S_%Y-%m-%d")
                    captured_path = TEMP_FOLDER / f"OptiA1_{ts}.jpg"
                    latest_frame.save(captured_path)
                    img_copy = latest_frame.copy(); img_copy.putalpha(mask)
                    imgtk = ImageTk.PhotoImage(image=img_copy)
                    right_id = cv.create_image(754.0, 297.0, image=imgtk)
                    img_refs["captured_right"] = imgtk
                win.after(5000, lambda: cv.itemconfigure(img_ids["interrupt_light"], state="hidden"))

            prev_flag = flag if prev_flag is not None else flag
    except Exception as e:
        logging.error(f"File monitor: {e}")
    win.after(200, monitor_file)

# ===== Subprocess Handling =====
subproc_handle = None
def run_script():
    global subproc_handle
    try:
        if platform.system() == "Windows":
            subproc_handle = subprocess.Popen([sys.executable, str(SCRIPT)],
                                              creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            subproc_handle = subprocess.Popen([sys.executable, str(SCRIPT)], start_new_session=True)
        logging.info("Interrupt script started")
    except Exception as e:
        logging.error(f"Start script error: {e}")

# ===== Start after Camera Ready =====
def start_when_ready():
    if camera_ready:
        run_script()
        monitor_file()
    else:
        win.after(100, start_when_ready)

threading.Thread(target=init_cam, daemon=True).start()
threading.Thread(target=monitor_stable_log, daemon=True).start()
update_cam(); update_time()
win.after(100, start_when_ready)

# ===== Close =====
def on_close():
    if cap: cap.release()
    if subproc_handle and subproc_handle.poll() is None:
        try:
            if platform.system() == "Windows":
                subproc_handle.send_signal(signal.CTRL_BREAK_EVENT)
                time.sleep(0.5)
                subproc_handle.terminate()
            else:
                os.killpg(os.getpgid(subproc_handle.pid), signal.SIGTERM)
            logging.info("Subprocess terminated")
        except Exception as e:
            logging.error(f"Error terminating subprocess: {e}")
    win.destroy()

win.protocol("WM_DELETE_WINDOW", on_close)
win.resizable(False, False)
win.mainloop()
