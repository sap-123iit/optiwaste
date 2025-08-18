from pathlib import Path
from tkinter import Tk, Canvas, PhotoImage
import threading
import cv2
from PIL import Image, ImageTk, ImageDraw

# Configuration
ASSETS_PATH = Path(r"E:\Forgevision\Optiwaste\Device\optiwaste\build\assets\frame0")

def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)

# Image configurations (inline instead of CSV)
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

# Text configurations (inline instead of CSV)
text_configs = [
    {"key": "WEIGHT_TEXT", "text": "0.05 kg", "x_pos": 824.0, "y_pos": 495.0, "color": "#155E24", "font": ("Inter Bold", -40)},
    {"key": "TIME_TEXT", "text": "18:49", "x_pos": 805.0, "y_pos": 13.0, "color": "#727272", "font": ("Inter Bold", -40)},
    {"key": "STATUS_LABEL_TEXT", "text": "System status", "x_pos": 55.0, "y_pos": 495.0, "color": "#06552A", "font": ("Inter Bold", -20)},
    {"key": "STATUS_TEXT", "text": "Ready to Scan", "x_pos": 87.0, "y_pos": 533.0, "color": "#727272", "font": ("Inter Bold", -20)}
]

# Tkinter window setup
window = Tk()
window.geometry("1023x600")
window.configure(bg="#F5F5F3")

canvas = Canvas(window, bg="#F5F5F3", height=600, width=1023, bd=0, highlightthickness=0, relief="ridge")
canvas.place(x=0, y=0)

# Load and place images
image_refs = {}
for img_data in image_configs:
    img = PhotoImage(file=relative_to_assets(img_data["file_name"]))
    img_id = canvas.create_image(img_data["x_pos"], img_data["y_pos"], image=img)
    image_refs[img_data["variable_name"]] = (img, img_id)

# Load and place texts
for text_data in text_configs:
    canvas.create_text(
        text_data["x_pos"],
        text_data["y_pos"],
        anchor="nw",
        text=text_data["text"],
        fill=text_data["color"],
        font=text_data["font"]
    )

# Camera settings
cap = None
camera_ready = False
PREVIEW_WIDTH = 410
PREVIEW_HEIGHT = 240
PREVIEW_X = 262.0
PREVIEW_Y = 298.0
CORNER_RADIUS = 25

video_canvas_id = canvas.create_image(PREVIEW_X, PREVIEW_Y, image=None)

def create_rounded_mask(w, h, r):
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, w, h), r, fill=255)
    return mask

mask = create_rounded_mask(PREVIEW_WIDTH, PREVIEW_HEIGHT, CORNER_RADIUS)

def initialize_camera():
    global cap, camera_ready
    try:
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FPS, 30)
        camera_ready = True
    except Exception as e:
        print(f"Error initializing camera: {e}")

def update_camera():
    if not camera_ready:
        window.after(100, update_camera)
        return

    ret, frame = cap.read()
    if ret:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (PREVIEW_WIDTH, PREVIEW_HEIGHT))
        img = Image.fromarray(frame)
        img.putalpha(mask)
        imgtk = ImageTk.PhotoImage(image=img)
        canvas.itemconfig(video_canvas_id, image=imgtk)
        image_refs["video_feed"] = imgtk

    window.after(15, update_camera)

# Start camera thread
threading.Thread(target=initialize_camera, daemon=True).start()
update_camera()

def on_close():
    global cap
    if cap:
        cap.release()
    window.destroy()

window.protocol("WM_DELETE_WINDOW", on_close)
window.resizable(False, False)
window.mainloop()
