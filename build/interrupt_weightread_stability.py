import time, subprocess, os

# ---------- Load Config ----------
def load_config(file="config.txt"):
    cfg = {}
    with open(os.path.join(os.path.dirname(__file__), file)) as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                cfg[k] = v
    return cfg

cfg = load_config()

# Paths
gen_script = cfg["RAW_DATA_SCRIPT"]
raw_file   = os.path.join(os.path.dirname(gen_script), "raw_interrupt_weight.txt")
out_file   = cfg["DATA_FILE"]
log_file   = cfg["STABLE_LOG_FILE"]

# Stability parameters
THRESHOLD, COUNT, DURATION = 0.05, 4, 8

# State
capture, start_time, history = False, None, []
proc = None

def read_raw():
    try:
        s = open(raw_file).read().strip()
        i, w = s.split(",")
        return int(i), float(w.replace(" kg", "").strip())
    except: return 0, 0.0

def write_out(i, w): open(out_file,"w").write(f"{i},{w:.2f} kg")
def log_weight(w): open(log_file,"a").write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Stable weight: {w:.2f} kg\n")
def stable(ws): return len(ws) >= COUNT and max(ws[-COUNT:]) - min(ws[-COUNT:]) <= THRESHOLD

def start_gen():
    global proc
    if not proc:
        print("Launching generator...")
        proc = subprocess.Popen(["start","cmd","/k","python",gen_script], shell=True)

def stop_gen():
    if proc: subprocess.call(f"taskkill /F /T /PID {proc.pid}", shell=True)

# --- Run ---
start_gen()
try:
    while True:
        intr, w = read_raw()
        if not capture:
            if intr==1:
                capture, start_time, history = True, time.time(), [w]
                write_out(1,w); print(f"[NORMAL→CAPTURE] {w:.2f} kg")
            else:
                write_out(0,0.0); print("[NORMAL] Interrupt=0")
        else:
            history.append(w); write_out(1,w)
            print(f"[CAPTURE] {w:.2f} kg (elapsed={time.time()-start_time:.1f}s)")
            if time.time()-start_time >= DURATION:
                if stable(history):
                    fw = sum(history[-COUNT:])/COUNT
                    log_weight(fw); print(f"[STABLE] {fw:.2f} kg → Back to normal")
                    capture = False
                else: print("[NOT STABLE] Continuing capture...")
        time.sleep(1)
except KeyboardInterrupt:
    print("\nStopping...")
finally:
    stop_gen()
