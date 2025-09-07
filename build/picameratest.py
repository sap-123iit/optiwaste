#!/usr/bin/env python3
# Minimal preview using the SAME camera lines/patterns as in your gui9.py

from tkinter import Tk, Canvas
from PIL import Image, ImageTk, ImageDraw
from picamera2 import Picamera2
import time

# ---- same preview geometry you use in gui9 ----
PREVIEW_W, PREVIEW_H = 410, 240
PREVIEW_X, PREVIEW_Y = 262.0, 298.0
RADIUS = 25
ROTATE_RIGHT_90 = True   # set False if you don't want 90° right rotation

# ---- Tk / Canvas (simple fixed window like your GUI) ----
win = Tk()
win.geometry("1023x600")
win.configure(bg="#F5F5F3")
win.title("Picamera2 Preview (IMX708)")

cv = Canvas(win, bg="#F5F5F3", height=600, width=1023, bd=0, highlightthickness=0)
cv.place(x=0, y=0)

# one image item to hold the live preview (same approach as gui9)
left_video_id = cv.create_image(PREVIEW_X, PREVIEW_Y, image=None)

# rounded-corner mask (same as gui9)
mask = Image.new("L", (PREVIEW_W, PREVIEW_H), 0)
ImageDraw.Draw(mask).rounded_rectangle((0, 0, PREVIEW_W, PREVIEW_H), RADIUS, fill=255)

# keep a reference to PhotoImage to prevent GC
img_ref = {"live": None}

# ---- Picamera2 init: SAME lines used in your gui9 ----
picam2 = None
camera_ready = False
latest_frame = None

def init_cam():
    global picam2, camera_ready
    try:
        picam2 = Picamera2()
        # Request frames at the preview box size in RGB888 (PIL-friendly)
        cfg = picam2.create_preview_configuration(
            main={"size": (PREVIEW_W, PREVIEW_H), "format": "RGB888"}
        )
        picam2.configure(cfg)
        picam2.start()
        camera_ready = True
        print("CSI camera initialized (Picamera2, RGB888).")
    except Exception as e:
        print("CSI camera init failed:", e)
        camera_ready = False

def capture_frame():
    """SAME logic as gui9: capture_array -> optional rotate -> resize -> store PIL."""
    global latest_frame
    if not camera_ready:
        return False
    try:
        frame = picam2.capture_array()          # RGB numpy array
        pil_im = Image.fromarray(frame)         # to PIL

        if ROTATE_RIGHT_90:
            # PIL rotates CCW; -90 gives us a 90° right rotation
            pil_im = pil_im.rotate(-90, expand=True)

        if pil_im.size != (PREVIEW_W, PREVIEW_H):
            pil_im = pil_im.resize((PREVIEW_W, PREVIEW_H), Image.Resampling.LANCZOS)

        latest_frame = pil_im
        return True
    except Exception as e:
        print("Frame capture failed:", e)
        return False

def update_cam():
    if camera_ready and capture_frame():
        img_copy = latest_frame.copy()
        img_copy.putalpha(mask)
        imgtk = ImageTk.PhotoImage(image=img_copy)
        cv.itemconfig(left_video_id, image=imgtk)
        img_ref["live"] = imgtk  # pin reference
    # ~60fps-ish (15 ms). Use 33 for ~30fps if you prefer.
    win.after(15, update_cam)

def on_close():
    try:
        if picam2:
            picam2.stop()
    except Exception:
        pass
    win.destroy()

win.protocol("WM_DELETE_WINDOW", on_close)

# ---- run ----
init_cam()
win.after(50, update_cam)
win.mainloop()
