import sqlite3, json, os, smtplib, ssl, requests
from datetime import datetime
import paho.mqtt.publish as publish

DB_PATH = "energy_system.db"
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "")

MAX_NORMAL_CONSUMPTION_MW = 5000     # قيمة مثال - عدّلها حسب قياساتك الفعلية
IDLE_LEAK_THRESHOLD_MW = 200         # أي استهلاك أعلى من كده والحمل "OFF" = تسريب

known_relay_states = {}  # يُحدَّث من ai/relay أو من الأوامر الصادرة

def send_telegram(message: str):
    if not TELEGRAM_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=5)

def send_email(subject: str, message: str):
    if not ALERT_EMAIL:
        return
    # عدّل بيانات السيرفر حسب مزود البريد المستخدم
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
        server.sendmail(os.environ["SMTP_USER"], ALERT_EMAIL, f"Subject: {subject}\n\n{message}")

def trigger_alert(alert_type: str, severity: str, message: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO alerts(type, message, severity, ts) VALUES (?,?,?,?)",
                 (alert_type, message, severity, datetime.utcnow().isoformat()))
    conn.commit(); conn.close()

    payload = {"type": alert_type, "severity": severity, "message": message,
               "ts": datetime.utcnow().isoformat()}
    publish.single("alerts/system", json.dumps(payload), hostname="localhost")  # يوصل لجرس الـ ESP32

    send_telegram(f"⚠️ [{severity.upper()}] {message}")
    if severity == "high":
        send_email(f"System Alert: {alert_type}", message)

def check_consumption_rules(energy_payload: dict, soc: float):
    tile_id = energy_payload["tile_id"]
    power = energy_payload["power_mw"]
    relay_state = known_relay_states.get("corridor_light", "OFF")

    if relay_state == "OFF" and power > IDLE_LEAK_THRESHOLD_MW:
        trigger_alert("leak", "high", f"تيار تسريب مكتشف على {tile_id} أثناء إيقاف الحمل رسميًا")

    if power > MAX_NORMAL_CONSUMPTION_MW:
        trigger_alert("excess_consumption", "medium", f"استهلاك زائد عن الطبيعي على {tile_id}: {power} mW")

    if soc < 15:
        trigger_alert("low_storage", "medium", "مستوى شحن الوحدة التخزينية منخفض جدًا")