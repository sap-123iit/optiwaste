from pathlib import Path
from tkinter import Tk, Canvas, PhotoImage
import csv

OUTPUT_PATH = Path(__file__).parent

# Read config.txt
config = {}
with open(OUTPUT_PATH / "config.txt", "r") as config_file:
    for line in config_file:
        key, value = line.strip().split("=")
        config[key] = value
ASSETS_PATH = Path(config["ASSETS_PATH"])
IMAGE_CONFIG_PATH = Path(config["IMAGE_CONFIG_PATH"])
TEXT_CONFIG_PATH = Path(config["TEXT_CONFIG_PATH"])

def relative_to_assets(path: str) -> Path: return ASSETS_PATH / Path(path)

window = Tk()
window.geometry("1023x600"); window.configure(bg="#F5F5F3")

canvas = Canvas(window, bg="#F5F5F3", height=600, width=1023, bd=0, highlightthickness=0, relief="ridge")
canvas.place(x=0, y=0)

# Load images from CSV
image_refs = {}
with open(OUTPUT_PATH / IMAGE_CONFIG_PATH, newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        var_name = row['variable_name']
        img = PhotoImage(file=relative_to_assets(row['file_name']))
        img_id = canvas.create_image(float(row['x_pos']), float(row['y_pos']), image=img)
        image_refs[var_name] = (img, img_id)

# Load text from CSV
text_refs = {}
with open(OUTPUT_PATH / TEXT_CONFIG_PATH, newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        text_id = row['text_id']
        text_id = canvas.create_text(float(row['x_pos']), float(row['y_pos']), anchor="nw", text=row['text'], fill=row['color'], font=(row['font_name'], int(row['font_size'])))
        text_refs[text_id] = text_id

window.resizable(False, False); window.mainloop()