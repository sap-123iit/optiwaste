#loading text and image parameters from csv files

from pathlib import Path
from tkinter import Tk, Canvas, PhotoImage
import threading
import cv2
from PIL import Image, ImageTk, ImageDraw
import csv

OUTPUT_PATH = Path(__file__).parent

# Read config.txt
config = {}
with open(OUTPUT_PATH / "config.txt", "r") as config_file:
    for line in config_file:
        key, value = line.strip().split("=")
        config[key] = value
ASSETS_PATH = Path(config["ASSETS_PATH"])

def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)

# Load image configurations from CSV
def load_images_csv():
    images = []
    with open(OUTPUT_PATH / "image_config.csv", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            images.append({
                "variable_name": row["variable_name"],
                "file_name": row["file_name"],
                "x_pos": float(row["x_pos"]),
                "y_pos": float(row["y_pos"])
            })
    return images

# Load text configurations from CSV
def load_texts_csv():
    texts = []
    with open(OUTPUT_PATH / "text_config.csv", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            texts.append({
                "key": row["key"],
                "text": row["text"],
                "x_pos": float(row["x_pos"]),
                "y_pos": float(row["y_pos"]),
                "color": row["color"],
                "font": (row["font_name"], int(row["font_size"]))
            })
    return texts

# Tkinter window
window = Tk()
window.geometry("1023x600")
window.configure(bg="#F5F5F3")

canvas = Canvas(window, bg="#F5F5F3", height=600, width=1023, bd=0, highlightthickness=0, relief="ridge")
canvas.place(x=0, y=0)

# Load and place images
image_refs = {}
for img_data in load_images_csv():
    img = PhotoImage(file=relative_to_assets(img_data["file_name"]))
    img_id = canvas.create_image(img_data["x_pos"], img_data["y_pos"], image=img)
    image_refs[img_data["variable_name"]] = (img, img_id)

# Load and place texts
for text_data in load_texts_csv():
    canvas.create_text(
        text_data["x_pos"],
        text_data["y_pos"],
        anchor="nw",
        text=text_data["text"],
        fill=text_data["color"],
        font=text_data["font"]
    )

# Camera setup
cap = None
camera_ready = False
PREVIEW_WIDTH = 410
PREVIEW_HEIGHT = 240
PREVIEW_X = 262.0
PREVIEW_Y = 298.0
CORNER_RADIUS = 25  # rounded corners

# Create placeholder for video feed
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
        img.putalpha(mask)  # apply rounded corners
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
