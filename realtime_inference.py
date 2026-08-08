import json, joblib, numpy as np, pandas as pd
from collections import deque
from datetime import datetime
import paho.mqtt.client as mqtt
import tensorflow as tf
import alert_manager

occupancy_model = joblib.load("models/occupancy_classifier.joblib")
lstm_model = tf.keras.models.load_model("models/energy_forecast_lstm.keras")
energy_scaler = joblib.load("models/energy_scaler.joblib")
autoencoder = tf.keras.models.load_model("models/tile_anomaly_autoencoder.keras")
anomaly_scaler = joblib.load("models/anomaly_scaler.joblib")
anomaly_cfg = json.load(open("models/anomaly_config.json"))

rssi_buffer = deque(maxlen=5)      # نافذة 5 ثواني
energy_buffer = deque(maxlen=30)   # نافذة LSTM
storage_soc = 50.0                 # % - يُحدَّث من قراءات الطاقة الفعلية

client = mqtt.Client()

def extract_rssi_features(buf):
    arr = np.array(buf)
    return np.array([[arr.mean(), arr.std(), arr.min(), arr.max(),
                       arr.max() - arr.min(), np.mean(np.abs(np.diff(arr)))]])

def decide_relay(occupancy_state, soc):
    """منطق القاطع الذكي: أولوية للطاقة المخزنة، ثم الشبكة عند الحاجة فقط"""
    if soc >= 30:
        return "ON" if occupancy_state != "empty" else "OFF"
    elif soc >= 15:
        return "ON" if occupancy_state == "multiple_moving" else "OFF"
    else:
        return "OFF"  # حماية البطارية، الأحمال الحرجة فقط تتغذى من الشبكة (منطق منفصل)

def on_message(client, userdata, msg):
    global storage_soc
    payload = json.loads(msg.payload.decode())

    if msg.topic.startswith("occupancy/rssi/"):
        rssi_buffer.append(payload["rssi"])
        if len(rssi_buffer) == rssi_buffer.maxlen:
            feats = extract_rssi_features(rssi_buffer)
            state = occupancy_model.predict(feats)[0]
            client.publish("ai/occupancy/state", json.dumps(
                {"state": state, "ts": datetime.utcnow().isoformat()}))
            relay_cmd = decide_relay(state, storage_soc)
            client.publish("actuators/relay/corridor_light/cmd", relay_cmd)

    elif msg.topic.startswith("energy/tiles/"):
        storage_soc = min(100.0, storage_soc + payload["energy_wh_delta"] * 2)  # تبسيط تقديري
        energy_buffer.append(payload["power_mw"])
        if len(energy_buffer) == energy_buffer.maxlen:
            seq = energy_scaler.transform(np.array(energy_buffer).reshape(-1, 1)).reshape(1, -1, 1)
            pred_scaled = lstm_model.predict(seq, verbose=0)
            pred = energy_scaler.inverse_transform(pred_scaled)[0][0]
            client.publish("ai/energy/forecast", json.dumps(
                {"predicted_power_mw": float(pred), "ts": datetime.utcnow().isoformat()}))

            # كشف الشذوذ لكل بلاطة
            X = anomaly_scaler.transform(np.array(energy_buffer)[-1:].reshape(1, -1))
            recon = autoencoder.predict(X, verbose=0)
            error = float(np.mean(np.square(X - recon)))
            is_anomaly = error > anomaly_cfg["threshold"]
            if is_anomaly:
                alert_manager.trigger_alert("tile_fault", "high",
                    f"تراجع أداء بلاطة {payload['tile_id']} - يحتاج فحص")

        alert_manager.check_consumption_rules(payload, storage_soc)

client.on_message = on_message
client.connect("localhost", 1883, 60)
client.subscribe([("occupancy/rssi/+/telemetry", 0), ("energy/tiles/+/telemetry", 0)])

if __name__ == "__main__":
    print("Real-time inference engine running...")
    client.loop_forever()