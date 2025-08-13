import random
import time

# File path (Windows format)
file_name = r"E:\Forgevision\Optiwaste\Device\optiwaste\build\raw_interrupt_weight.txt"

while True:
    # Randomly generate interrupt (0 or 1)
    interrupt = random.randint(0, 1)

    # Randomly generate weight between 0.2 and 1.0 kg (2 decimal places)
    weight = round(random.uniform(0.2, 1.0), 2)

    # Prepare the line to write
    line = f"{interrupt},{weight} kg"

    # Write to file
    with open(file_name, "w") as f:
        f.write(line)

    print(f"Data written to {file_name}: {line}")

    # Wait for 2 seconds before the next update
    time.sleep(2)