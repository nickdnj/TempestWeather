import time
import json
from overlay.tempest_udp_conditions import get_current_conditions

OUTPUT_PATH = "/tmp/tempest_latest.json"
INTERVAL = 60  # seconds

while True:
    try:
        data = get_current_conditions()
        with open(OUTPUT_PATH, "w") as f:
            json.dump(data, f)
        print(f"Updated {OUTPUT_PATH} with latest Tempest data.")
    except Exception as e:
        print(f"Error updating Tempest data: {e}")
    time.sleep(INTERVAL) 