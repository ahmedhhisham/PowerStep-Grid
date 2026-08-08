import json, sqlite3, csv, os
from datetime import datetime
import paho.mqtt.client as mqtt

DB_PATH = "energy_system.db"
CSV_BACKUP = "raw_backup.csv"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS readings_energy(
        id INTEGER PRIMARY KEY AUTOINCREMENT, tile_id TEXT, power_mw REAL,
        energy_wh_delta REAL, ts TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS readings_rssi(
        id INTEGER PRIMARY KEY AUTOINCREMENT, node_id TEXT, rssi REAL, ts TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS alerts(
        id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, message TEXT,
        severity TEXT, ts TEXT, resolved INTEGER DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS ai_results(
        id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT, payload TEXT, ts TEXT)""")
    conn.commit()
    return conn

conn = init_db()

def backup_csv(row: dict, source: str):
    exists = os.path.isfile(CSV_BACKUP)
    with open(CSV_BACKUP, "a", newline="") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["source", "data", "ts"])
        w.writerow([source, json.dumps(row), datetime.utcnow().isoformat()])

def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    topic = msg.topic
    c = conn.cursor()
    if topic.startswith("energy/tiles/"):
        c.execute("INSERT INTO readings_energy(tile_id, power_mw, energy_wh_delta, ts) VALUES (?,?,?,?)",
                   (payload["tile_id"], payload["power_mw"], payload["energy_wh_delta"], payload["ts"]))
        backup_csv(payload, "energy")
    elif topic.startswith("occupancy/rssi/"):
        c.execute("INSERT INTO readings_rssi(node_id, rssi, ts) VALUES (?,?,?)",
                   (payload["node_id"], payload["rssi"], payload["ts"]))
        backup_csv(payload, "rssi")
    elif topic == "alerts/system":
        c.execute("INSERT INTO alerts(type, message, severity, ts) VALUES (?,?,?,?)",
                   (payload["type"], payload["message"], payload["severity"], payload["ts"]))
    elif topic.startswith("ai/"):
        c.execute("INSERT INTO ai_results(kind, payload, ts) VALUES (?,?,?)",
                   (topic, json.dumps(payload), payload.get("ts", datetime.utcnow().isoformat())))
    conn.commit()

client = mqtt.Client()
client.on_message = on_message
client.connect("localhost", 1883, 60)
client.subscribe([("energy/tiles/+/telemetry", 0), ("occupancy/rssi/+/telemetry", 0),
                   ("alerts/system", 0), ("ai/#", 0)])

if __name__ == "__main__":
    print("Ingest service running...")
    client.loop_forever()