from pathlib import Path
from tkinter import Tk, Canvas, PhotoImage
import threading
import cv2
from PIL import Image, ImageTk
import time

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

# --- UI Settings ---
WEIGHT_TEXT = "0.05 kg"; WEIGHT_POS = (824.0, 495.0); WEIGHT_COLOR = "#155E24"; WEIGHT_FONT = ("Inter Bold", -40)
TIME_TEXT = "18:49"; TIME_POS = (805.0, 13.0); TIME_COLOR = "#727272"; TIME_FONT = ("Inter Bold", -40)
STATUS_LABEL_TEXT = "System status"; STATUS_LABEL_POS = (55.0, 495.0); STATUS_LABEL_COLOR = "#06552A"; STATUS_LABEL_FONT = ("Inter Bold", -20)
STATUS_TEXT = "Ready to Scan"; STATUS_POS = (87.0, 533.0); STATUS_COLOR = "#727272"; STATUS_FONT = ("Inter Bold", -20)

images = [
    {"variable_name": "right_canvas", "file_name": "rightcanvas.png", "x_pos": 748.0, "y_pos": 300.0},
    {"variable_name": "left_canvas", "file_name": "leftcanvas.png", "x_pos": 258.0, "y_pos": 293.0},
    {"variable_name": "interrupt_light", "file_name": "interruptlight.png", "x_pos": 262.0, "y_pos": 297.0},
    {"variable_name": "left_camera_pane", "file_name": "leftcamerapane.png", "x_pos": 262.0, "y_pos": 298.0},
    {"variable_name": "right_camera_pane", "file_name": "rightcamerapane.png", "x_pos": 754.0, "y_pos": 297.0},
    {"variable_name": "left_camera_heading", "file_name": "leftcameraheading.png", "x_pos": 124.0, "y_pos": 98.0},
    {"variable_name": "right_camera_heading", "file_name": "rightcameraheading.png", "x_pos": 641.0, "y_pos": 98.0},
    {"variable_name": "network_wifi", "file_name": "network_wifi.png", "x_pos": 969.0, "y_pos": 35.0},
    {"variable_name": "place_hand", "file_name": "placehand.png", "x_pos": 75.0, "y_pos": 544.0},
    {"variable_name": "optiwaste_logo", "file_name": "optiwastelogo.png", "x_pos": 166.0, "y_pos": 39.0},
]

window = Tk()
window.geometry("1023x600")
window.configure(bg="#F5F5F3")

canvas = Canvas(window, bg="#F5F5F3", height=600, width=1023, bd=0, highlightthickness=0, relief="ridge")
canvas.place(x=0, y=0)

# Load placeholder images
image_refs = {}
for img_data in images:
    var_name = img_data["variable_name"]
    img = PhotoImage(file=relative_to_assets(img_data["file_name"]))
    img_id = canvas.create_image(img_data["x_pos"], img_data["y_pos"], image=img)
    image_refs[var_name] = (img, img_id)

# Create text
canvas.create_text(WEIGHT_POS[0], WEIGHT_POS[1], anchor="nw", text=WEIGHT_TEXT, fill=WEIGHT_COLOR, font=WEIGHT_FONT)
canvas.create_text(TIME_POS[0], TIME_POS[1], anchor="nw", text=TIME_TEXT, fill=TIME_COLOR, font=TIME_FONT)
canvas.create_text(STATUS_LABEL_POS[0], STATUS_LABEL_POS[1], anchor="nw", text=STATUS_LABEL_TEXT, fill=STATUS_LABEL_COLOR, font=STATUS_LABEL_FONT)
canvas.create_text(STATUS_POS[0], STATUS_POS[1], anchor="nw", text=STATUS_TEXT, fill=STATUS_COLOR, font=STATUS_FONT)

# --- Camera Setup ---
cap = None
video_canvas_id = None
frame_ref = None
stop_thread = False

# Exact placeholder size — replace with actual size of left_camera_pane.png
LEFT_CAM_WIDTH = 428
LEFT_CAM_HEIGHT = 260
LEFT_CAM_X = 262.0
LEFT_CAM_Y = 298.0

def camera_thread():
    global cap, frame_ref, video_canvas_id
    time.sleep(0.5)  # Let UI start
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Camera not found")
        return

    while not stop_thread:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (LEFT_CAM_WIDTH, LEFT_CAM_HEIGHT))
        img = Image.fromarray(frame)
        frame_ref = ImageTk.PhotoImage(img)  # Keep reference to avoid GC

        if video_canvas_id is None:
            # Remove placeholder image so no flicker
            pane_img_id = image_refs["left_camera_pane"][1]
            canvas.delete(pane_img_id)
            # Create the camera feed image in the exact same position
            video_canvas_id = canvas.create_image(
                LEFT_CAM_X, LEFT_CAM_Y,
                image=frame_ref
            )
        else:
            canvas.itemconfig(video_canvas_id, image=frame_ref)

        time.sleep(0.03)  # ~30 FPS

threading.Thread(target=camera_thread, daemon=True).start()

def on_close():
    global stop_thread
    stop_thread = True
    if cap:
        cap.release()
    window.destroy()

window.protocol("WM_DELETE_WINDOW", on_close)
window.resizable(False, False)
window.mainloop()
