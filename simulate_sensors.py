import json, time, random, math
from datetime import datetime
import paho.mqtt.client as mqtt

BROKER = "localhost"
TILE_IDS = ["tile_1", "tile_2", "tile_3"]
NODE_IDS = ["corridor_node_1"]

client = mqtt.Client()
client.connect(BROKER, 1883, 60)

def busy_factor(hour):
    """محاكاة ذروة عند مواعيد تبديل المحاضرات (8, 10, 12, 16)"""
    peaks = [8, 10, 12, 16]
    factor = 0.05  # ضجيج خلفية بسيط دايمًا
    for p in peaks:
        factor += math.exp(-((hour - p) ** 2) / 0.5)
    return min(factor, 1.0)

def simulate_energy(tile_id, occupied_intensity):
    steps_this_tick = max(0, int(random.gauss(occupied_intensity * 5, 1)))
    energy_wh = steps_this_tick * random.uniform(0.0004, 0.0009)  # ~2 جول/خطوة بعد الفقد
    power_mw = (energy_wh * 3600 * 1000) / 5  # تقريبي لكل 5 ثواني
    return {
        "tile_id": tile_id,
        "steps": steps_this_tick,
        "power_mw": round(power_mw, 2),
        "energy_wh_delta": round(energy_wh, 5),
        "ts": datetime.utcnow().isoformat()
    }

def simulate_rssi(node_id, occupied_intensity):
    baseline = -55
    noise = random.gauss(0, 1.5 + occupied_intensity * 3)  # تذبذب أكبر مع وجود ناس
    return {"node_id": node_id, "rssi": round(baseline + noise, 1), "ts": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    print("Digital Twin simulator running... Ctrl+C للإيقاف")
    while True:
        hour = datetime.now().hour + datetime.now().minute / 60
        intensity = busy_factor(hour)
        for t in TILE_IDS:
            payload = simulate_energy(t, intensity)
            client.publish(f"energy/tiles/{t}/telemetry", json.dumps(payload))
        for n in NODE_IDS:
            payload = simulate_rssi(n, intensity)
            client.publish(f"occupancy/rssi/{n}/telemetry", json.dumps(payload))
        time.sleep(5)