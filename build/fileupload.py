#!/usr/bin/env python3
import requests, os, logging, time
from pathlib import Path

API_URL = "https://forgevision.ai/opti/uploadimageapi/upload_image.php"
BASE = Path(__file__).parent
cfg = {k.strip():v.strip() for k,v in(line.split("=",1) for line in open(BASE/"config.txt") if "=" in line)}
UPLOAD_LOG = BASE / "upload_log.txt"
UPLOAD_INTERVAL, MAX_RETRIES = 600, 3
IMAGE_DIR, DEVICE_NAME = BASE / cfg.get("SAVE_FOLDER", "saved"), cfg.get("DEVICE_NAME", "Opti02")
logging.basicConfig(filename=str(BASE/"uploader.log"), level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def get_uploaded_files():
    try:
        # Ensure upload log file exists
        UPLOAD_LOG.parent.mkdir(parents=True, exist_ok=True)
        if not UPLOAD_LOG.exists():
            UPLOAD_LOG.touch()
            logging.info("Created upload_log.txt file")
            
        with open(UPLOAD_LOG, 'r') as f: 
            return set(line.strip() for line in f if line.strip())
    except Exception as e:
        logging.error(f"Error reading upload log: {str(e)}")
        return set()

def log_uploaded_file(filename):
    try:
        with open(UPLOAD_LOG, 'a') as f: 
            f.write(f"{filename}\n")
            logging.info(f"Logged uploaded file: {filename}")
    except Exception as e:
        logging.error(f"Error logging uploaded file: {str(e)}")

def upload_file_with_retries(file_path):
    file_name, attempts = file_path.name, 0
    
    # Check if file still exists
    if not file_path.exists():
        logging.warning(f"File no longer exists: {file_name}")
        return False
        
    while attempts < MAX_RETRIES:
        try:
            logging.info(f"Attempt {attempts+1} for file: {file_name}")
            parts = file_name.split("_")
            if len(parts) != 4: 
                logging.error(f"Invalid filename format: {file_name}")
                return False
                
            device_name, time_date_part, date_part, weight_part = parts
            weight = float(weight_part.split(".")[0].replace("x", "."))
            timestamp = f"{date_part} {':'.join(time_date_part.split('-'))}"
            
            with open(file_path, "rb") as image_file:
                response = requests.post(API_URL, files={"image": image_file}, 
                                        data={"device_name": device_name, "timestamp": timestamp, "weight": weight}, 
                                        timeout=30)
            
            if response.status_code == 200:
                logging.info(f"Successfully uploaded {file_name}")
                log_uploaded_file(file_name)
                # Delete the file only after successful upload and logging
                try:
                    file_path.unlink()
                    logging.info(f"Deleted uploaded file: {file_name}")
                except Exception as e:
                    logging.error(f"Error deleting file {file_name}: {str(e)}")
                return True
                
            logging.warning(f"Upload attempt {attempts+1} failed for {file_name}. Status: {response.status_code}")
            
        except Exception as e:
            logging.error(f"Error during attempt {attempts+1} for {file_name}: {str(e)}")
        
        attempts += 1
        if attempts < MAX_RETRIES: 
            logging.info(f"Waiting 10 seconds before retry {attempts+1}")
            time.sleep(10)
            
    logging.error(f"All upload attempts failed for {file_name}")
    return False

def upload_cycle():
    try:
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        UPLOAD_LOG.parent.mkdir(parents=True, exist_ok=True)
        
        # Ensure upload log exists
        if not UPLOAD_LOG.exists():
            UPLOAD_LOG.touch()
            
        uploaded_files = get_uploaded_files()
        logging.info(f"Found {len(uploaded_files)} files in upload log")
        
        image_files = list(IMAGE_DIR.glob("*.jpg"))
        logging.info(f"Found {len(image_files)} image files to process")
        
        if not image_files:
            logging.info("No images to upload")
            return
            
        for file_path in image_files:
            if file_path.name not in uploaded_files:
                try:
                    if upload_file_with_retries(file_path):
                        logging.info(f"Successfully processed {file_path.name}")
                    else:
                        logging.warning(f"Failed to process {file_path.name} after retries")
                except Exception as e:
                    logging.error(f"Unexpected error processing {file_path.name}: {str(e)}")
            else:
                logging.info(f"File already uploaded: {file_path.name}")
                # Remove file if it's already in the log (already uploaded)
                try:
                    file_path.unlink()
                    logging.info(f"Removed already uploaded file: {file_path.name}")
                except Exception as e:
                    logging.error(f"Error removing file {file_path.name}: {str(e)}")
                
    except Exception as e:
        logging.error(f"Fatal error in upload cycle: {str(e)}")
        raise

def run_upload_service():
    logging.info("Starting upload service")
    while True:
        try:
            logging.info("Starting new upload cycle")
            upload_cycle()
            logging.info(f"Upload cycle completed. Waiting {UPLOAD_INTERVAL} seconds")
            time.sleep(UPLOAD_INTERVAL)
        except KeyboardInterrupt:
            logging.info("Upload service stopped by user")
            break
        except Exception as e:
            logging.error(f"Error in upload service: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    run_upload_service()