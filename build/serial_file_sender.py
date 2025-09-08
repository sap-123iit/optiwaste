# serial_file_sender.py
import serial
import time
import os
import queue
import threading

SERIAL_PORT = '/dev/ttyACM0'
BAUDRATE = 115200
INPUT_FILE = '/home/pi/opti1/serialinput.txt'
SEND_DELAY = 3  # seconds between sends

def serial_worker(ser, q):
    """Continuously send characters from the queue with a delay."""
    while True:
        char = q.get()  # blocking wait for next item
        if char is None:  # sentinel to exit
            break
        try:
            ser.write(char.encode('utf-8'))
            print(f"Sent '{char}' to serial port.")
        except Exception as e:
            print(f"Error sending to serial: {e}")
        time.sleep(SEND_DELAY)  # ensure gap
        q.task_done()

def main():
    ser = None
    try:
        ser = serial.Serial(
            port=SERIAL_PORT,
            baudrate=BAUDRATE,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        time.sleep(2)  # allow connection setup
        print(f"Serial connected at {SERIAL_PORT} ({BAUDRATE} baud).")

        q = queue.Queue()
        threading.Thread(target=serial_worker, args=(ser, q), daemon=True).start()

        last_char = None
        while True:
            try:
                if os.path.exists(INPUT_FILE):
                    with open(INPUT_FILE, 'r') as f:
                        content = f.read().strip()
                        if content:
                            if content != last_char:
                                q.put(content)  # enqueue for serial transmission
                                last_char = content
                time.sleep(0.1)
            except Exception as e:
                print(f"Error reading file: {e}")
                time.sleep(1)

    except KeyboardInterrupt:
        print("Program terminated by user.")
    finally:
        if ser and ser.is_open:
            ser.close()
            print("Serial connection closed.")

if __name__ == "__main__":
    main()
