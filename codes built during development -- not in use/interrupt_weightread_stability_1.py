import time
import subprocess
import os

# Paths
generator_script = r"E:\Forgevision\Optiwaste\Device\optiwaste\build\weight_interrupt_generator.py"
input_file = r"E:\Forgevision\Optiwaste\Device\optiwaste\build\raw_interrupt_weight.txt"
output_file = r"E:\Forgevision\Optiwaste\Device\optiwaste\build\final_weight_interrupt.txt"
log_file = r"E:\Forgevision\Optiwaste\Device\optiwaste\build\stable_weight_log.txt"

# Stability parameters
STABILITY_THRESHOLD = 0.05
STABILITY_COUNT = 4
CAPTURE_DURATION = 8

# State variables
capture_mode = False
capture_start_time = None
weight_history = []

def read_raw_file():
    """Reads interrupt and weight from the raw file."""
    try:
        with open(input_file, "r") as f:
            content = f.read().strip()
        interrupt_str, weight_str = content.split(",")
        interrupt = int(interrupt_str)
        weight = float(weight_str.replace(" kg", "").strip())
        return interrupt, weight
    except Exception:
        return 0, 0.00

def write_final_file(interrupt, weight):
    """Writes interrupt and weight to the final file."""
    with open(output_file, "w") as f:
        f.write(f"{interrupt},{weight:.2f} kg")

def log_stable_weight(weight):
    """Logs stable weight with timestamp."""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a") as f:
        f.write(f"{timestamp} - Stable weight: {weight:.2f} kg\n")

def is_weight_stable(weights):
    """Checks if weight difference stays within threshold for last N readings."""
    if len(weights) < STABILITY_COUNT:
        return False
    min_w = min(weights[-STABILITY_COUNT:])
    max_w = max(weights[-STABILITY_COUNT:])
    return (max_w - min_w) <= STABILITY_THRESHOLD

# Launch generator in a new console window (Windows specific)
print("Launching generator in a new console...")
subprocess.Popen(
    ["start", "cmd", "/k", "python", generator_script],
    shell=True
)

# Main loop
try:
    while True:
        interrupt, weight = read_raw_file()

        if not capture_mode:
            if interrupt == 1:
                capture_mode = True
                capture_start_time = time.time()
                weight_history.clear()
                weight_history.append(weight)
                write_final_file(1, weight)
                print(f"[NORMAL → CAPTURE] Interrupt=1, Weight={weight:.2f} kg")
            else:
                write_final_file(0, 0.00)
                print("[NORMAL] Interrupt=0 → Writing 0,0.00")
        else:
            weight_history.append(weight)
            write_final_file(1, weight)
            print(f"[CAPTURE] Weight={weight:.2f} kg (elapsed={time.time()-capture_start_time:.1f}s)")

            elapsed = time.time() - capture_start_time
            if elapsed >= CAPTURE_DURATION:
                if is_weight_stable(weight_history):
                    final_stable_weight = sum(weight_history[-STABILITY_COUNT:]) / STABILITY_COUNT
                    log_stable_weight(final_stable_weight)
                    print(f"[STABLE] Final weight={final_stable_weight:.2f} kg → Back to normal mode")
                    capture_mode = False
                else:
                    print("[NOT STABLE] Continuing capture...")

        time.sleep(1)

except KeyboardInterrupt:
    print("\nStopping...")
