import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_device_data(sensor_id, device_type, start_date, days=365):
    print(f"Generating 1-year historical data for: {sensor_id} ({device_type})...")
    
    # Generate timestamp range hour by hour
    dates = [start_date + timedelta(hours=i) for i in range(days * 24)]
    
    power_readings = []
    voltage_readings = []
    accumulated_energy_kwh = 0.0
    energy_readings_kwh = []
    
    # Configure random number generator for reproducibility
    rng = np.random.default_rng(seed=42 + len(sensor_id))
    
    for current_date in dates:
        hour = current_date.hour
        is_weekend = current_date.weekday() >= 5
        power_w = 0.0
        
        grid_load_factor = 2.0 if hour in [9, 10, 11, 19, 20, 21] else 0.0
        voltage_v = 230.0 - grid_load_factor + rng.uniform(-2.5, 2.5)
        voltage_readings.append(round(voltage_v, 1))
        
        # FRIDGE (Constant baseline + cyclic compressor spikes)
        if device_type == "fridge":
            base_load = 40.0 + rng.uniform(-5, 5)
            if rng.random() > 0.4:
                compressor_load = 90.0 + rng.uniform(-10, 10)
            else:
                compressor_load = 0.0
            power_w = base_load + compressor_load
            
        # OVEN (Intermittent high load during lunch/dinner hours)
        elif device_type == "oven":
            if hour in [13, 14, 20, 21]:
                usage_probability = 0.35 if is_weekend else 0.15
                if rng.random() < usage_probability:
                    power_w = 1800.0 + rng.uniform(-300, 400)
            elif hour in [9, 10] and is_weekend:
                if rng.random() < 0.1:
                    power_w = 1500.0
                    
        # WASHING MACHINE (Episodic high cycles a few times per week)
        elif device_type == "washing_machine":
            if hour in range(9, 22):
                washing_probability = 0.08 if is_weekend else 0.03
                if rng.random() < washing_probability:
                    power_w = rng.choice([2000.0, 400.0, 600.0], p=[0.3, 0.5, 0.2])
                    
        # Ensure no negative power
        power_w = max(0.0, power_w)
        power_readings.append(round(power_w, 2))
        
        # Calculate energy consumed: Wh = W * 1 hour
        hourly_energy_kwh = power_w / 1000.0
        accumulated_energy_kwh += hourly_energy_kwh
        energy_readings_kwh.append(round(accumulated_energy_kwh, 4))
        
    df = pd.DataFrame({
        "timestamp": dates,
        "sensor_id": sensor_id,
        "power_w": power_readings,
        "voltage_v": voltage_readings,
        "total_energy_kwh": energy_readings_kwh
    })
    
    return df

def main():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(BASE_DIR, 'data')
    os.makedirs(output_dir, exist_ok=True)
    
    start_date = datetime.now() - timedelta(days=365)
    
    device_configs = [
        {"id": "sensor.shelly_fridge_kitchen", "type": "fridge"},
        {"id": "sensor.shelly_oven_kitchen", "type": "oven"},
        {"id": "sensor.shelly_washing_machine_laundry", "type": "washing_machine"}
    ]
    
    for device in device_configs:
        df = generate_device_data(device["id"], device["type"], start_date)
        
        filename = f"device-{device['id'].replace('_', '-')}-data.csv"
        file_path = os.path.join(output_dir, filename)
        
        df.to_csv(file_path, index=False)
        print(f"Successfully saved: {file_path} ({len(df)} records)\n")

if __name__ == "__main__":
    main()