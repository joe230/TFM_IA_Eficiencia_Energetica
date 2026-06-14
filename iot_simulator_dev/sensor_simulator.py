import os
import time
import requests
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

HA_API = os.getenv("HA_API")
HA_TOKEN = os.getenv("HA_TOKEN")

HEADERS = {
    "Authorization": f"Bearer {HA_TOKEN}",
    "Content-Type": "application/json",
}

def generate_live_telemetry(sensor_id, device_type):
    """Generates realistic smart plug metrics based on the actual current time."""
    now = datetime.now()
    current_hour = now.hour
    is_weekend = now.weekday() >= 5
    
    rng = np.random.default_rng()
    
    voltage_v = round(230.0 + rng.uniform(-1.5, 1.5), 1)
    power_w = 0.0
    
    # FRIDGE (Cyclic behavior)
    if device_type == "fridge":
        base_load = 42.0 + rng.uniform(-2, 2)
        compressor_load = 95.0 + rng.uniform(-5, 5) if rng.random() > 0.5 else 0.0
        power_w = base_load + compressor_load
        
    # OVEN (Active only around lunch or dinner times)
    elif device_type == "oven":
        if current_hour in [13, 14, 20, 21]:
            power_w = 1900.0 + rng.uniform(-200, 200) if rng.random() < 0.7 else 0.0
            
    # WASHING MACHINE (Active mostly during weekend daytime)
    elif device_type == "washing_machine":
        if is_weekend and current_hour in range(10, 18):
            power_w = rng.choice([1800.0, 500.0, 0.0], p=[0.4, 0.4, 0.2])

    power_w = max(0.0, round(power_w, 2))
    return power_w, voltage_v

def start_live_streaming_loop():
    print("IoT Live Simulator Engine Started...")
    print(f"Targeting Home Assistant Endpoint: {HA_API}")
    
    devices = [
        {"id": "sensor.shelly_fridge_kitchen", "type": "fridge"},
        {"id": "sensor.shelly_oven_kitchen", "type": "oven"},
        {"id": "sensor.shelly_washing_machine_laundry", "type": "washing_machine"}
    ]
    
    while True:
        print(f"\n--- [Live Broadcast: {datetime.now().strftime('%H:%M:%S')}] ---")
        
        for device in devices:
            entity_id = device["id"]
            power_w, voltage_v = generate_live_telemetry(entity_id, device["type"])
            
            endpoint_url = f"{HA_API}/{entity_id}"
            payload = {
                "state": str(power_w),
                "attributes": {
                    "unit_of_measurement": "W",
                    "device_class": "power",
                    "state_class": "measurement",
                    "voltage": voltage_v,
                    "friendly_name": entity_id.replace("sensor.", "").replace("_", " ").title()
                }
            }
            
            try:
                response = requests.post(endpoint_url, json=payload, headers=HEADERS)
                if response.status_code in [200, 201]:
                    print(f"[BROADCASTED] {entity_id} -> {power_w} W | {voltage_v} V")
                else:
                    print(f"[HA ERROR] {response.status_code}: {response.text}")
            except Exception as e:
                print(f"Network error connecting to Home Assistant: {e}")
                
        time.sleep(10)

if __name__ == "__main__":
    start_live_streaming_loop()