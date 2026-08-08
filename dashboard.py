import streamlit as st
import pandas as pd, sqlite3, json
import plotly.graph_objects as go
import plotly.express as px
import paho.mqtt.publish as publish
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="PowerStep - Live Dashboard", layout="wide")
st_autorefresh(interval=5000, key="refresh")

DB_PATH = "energy_system.db"
conn = sqlite3.connect(DB_PATH, check_same_thread=False)

# --- تحقق من التنبيهات غير المحلولة ---
alerts = pd.read_sql("SELECT * FROM alerts WHERE resolved=0 ORDER BY ts DESC LIMIT 5", conn)
if not alerts.empty and (alerts["severity"] == "high").any():
    st.error(f"🚨 تنبيه عاجل: {alerts.iloc[0]['message']}")

st.title("⚡ PowerStep Grid — Live Dashboard")

energy = pd.read_sql("SELECT * FROM readings_energy ORDER BY id DESC LIMIT 500", conn, parse_dates=["ts"])
latest_gen = energy["power_mw"].head(20).mean() if not energy.empty else 0
consumption_est = latest_gen * 0.9  # مثال - اربطها بقراءة ACS712 الفعلية

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.plotly_chart(go.Figure(go.Indicator(mode="gauge+number", value=latest_gen,
        title={"text": "التوليد اللحظي (mW)"}, gauge={"axis": {"range": [0, 3000]}})),
        use_container_width=True)
with col2:
    st.plotly_chart(go.Figure(go.Indicator(mode="gauge+number", value=consumption_est,
        title={"text": "الاستهلاك اللحظي (mW)"}, gauge={"axis": {"range": [0, 3000]}})),
        use_container_width=True)
with col3:
    self_suff = min(100, (latest_gen / consumption_est * 100) if consumption_est else 0)
    st.plotly_chart(go.Figure(go.Indicator(mode="gauge+number", value=self_suff,
        title={"text": "نسبة الاكتفاء الذاتي %"})), use_container_width=True)
with col4:
    st.metric("حالة شحن التخزين (SoC)", "68%")  # اربطها بمتغير storage_soc الفعلي

st.subheader("📈 التوليد مقابل الاستهلاك التراكمي")
if not energy.empty:
    fig = px.line(energy.sort_values("ts"), x="ts", y="power_mw", color="tile_id")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("🔥 خريطة كثافة الحركة (RSSI Heat Strip)")
rssi = pd.read_sql("SELECT * FROM readings_rssi ORDER BY id DESC LIMIT 200", conn, parse_dates=["ts"])
if not rssi.empty:
    st.plotly_chart(px.imshow([rssi["rssi"].values], aspect="auto",
        color_continuous_scale="Greens"), use_container_width=True)

st.subheader("🎛️ لوحة التحكم اليدوي بالأحمال")
c1, c2 = st.columns(2)
if c1.button("تشغيل إضاءة الممر"):
    publish.single("actuators/relay/corridor_light/cmd", "ON", hostname="localhost")
if c2.button("إيقاف إضاءة الممر"):
    publish.single("actuators/relay/corridor_light/cmd", "OFF", hostname="localhost")

st.subheader("💰 حاسبة التوفير المالي والبيئي")
tariff = st.number_input("سعر الكيلوواط/ساعة بالجنيه (حدّثه من فاتورتكم الفعلية)", value=1.5)
co2_factor = st.number_input("معامل الانبعاثات kgCO2/kWh (راجعه من مصدر رسمي محدّث)", value=0.45)
total_wh = energy["power_mw"].sum() / 1000 / 3600 if not energy.empty else 0
st.write(f"الطاقة المحصودة التراكمية: **{total_wh:.3f} Wh** | "
         f"التوفير المقدر: **{total_wh/1000*tariff:.4f} جنيه** | "
         f"CO2 الموفر: **{total_wh/1000*co2_factor*1000:.2f} جرام**")

st.subheader("📋 سجل التنبيهات")
all_alerts = pd.read_sql("SELECT * FROM alerts ORDER BY id DESC LIMIT 20", conn)
st.dataframe(all_alerts, use_container_width=True)