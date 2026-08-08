# ⚡ PowerStep — نظام إدارة الطاقة والإشغال الذكي

![Status](https://img.shields.io/badge/status-prototype-yellow)
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Platform](https://img.shields.io/badge/platform-ESP32-000000)

> نظام هجين IoT × AI لحصاد الطاقة الحركية من خطوات المشاة عبر بلاط بيزوكهربائي، واستشعار الإشغال بدون أي حساسات مادية عبر تذبذب إشارة الواي فاي (RSSI)، مع خط بيانات كامل، ثلاثة نماذج ذكاء اصطناعي (تصنيف إشغال، تنبؤ بالطاقة، كشف شذوذ للصيانة التنبؤية)، لوحة تحكم حية، ونظام إنذار فوري متعدد القنوات.

**English:** A hybrid IoT + AI energy system harvesting kinetic energy from footsteps via piezoelectric floor tiles, sensing occupancy through WiFi RSSI fluctuation (no cameras, no PIR sensors), with a full data pipeline, three AI models (occupancy classification, LSTM energy forecasting, autoencoder-based anomaly/predictive-maintenance detection), a live Streamlit dashboard, and multi-channel real-time alerting (Telegram / Email / on-device buzzer).

Developed by **NovAI team** 

---

## 🧭 نظرة عامة

المشروع يعالج مشكلتين معًا: هدر الطاقة الحركية الناتجة عن الخطوات في الممرات، والقصور التقليدي في استشعار الإشغال (حساسات PIR تفشل مع الأشخاص الساكنين، والكاميرات تثير مخاوف خصوصية). الحل: بلاط بيزوكهربائي لحصاد الطاقة + عقدة ESP32 تقرأ تذبذب إشارة الواي فاي الموجودة أصلًا في المبنى لتحديد الإشغال بدقة — مغذّى بخط بيانات ونماذج ذكاء اصطناعي فعلية قابلة للتشغيل والتدريب، وليس مجرد عرض توضيحي.

> 🔒 **خصوصية:** استشعار الواي فاي يقيس فقط قوة الإشارة الوصفية (RSSI) دون فك حزم البيانات أو تخزين عناوين MAC لأي جهاز — لا تُجمع أي بيانات شخصية.

---

## ✨ الميزات الرئيسية

- 🔋 حصاد طاقة حركي هجين مع الشبكة العامة.
- 📡 استشعار إشغال لاسلكي (WiFi RSSI) بدون عتاد إضافي وبدون كاميرات.
- 🧪 **توأم رقمي (Digital Twin)** — `simulate_sensors.py` يشغّل كل المنظومة بدون أي بلاط فعلي.
- 🗄️ خط بيانات كامل: MQTT → SQLite/CSV → Parquet.
- 🤖 تصنيف حالة الإشغال (Random Forest / SVM).
- 🔮 تنبؤ بالطاقة القادمة بشبكة LSTM.
- 🚨 كشف شذوذ بـ Autoencoder للصيانة التنبؤية وكشف تسريب الطاقة.
- 🧠 محرك استدلال لحظي يربط النماذج الثلاثة بقرار تحكم فعلي في الأحمال.
- 📊 لوحة تحكم حية (Streamlit) + رمز QR لمتابعة اللجنة من موبايلاتهم مباشرة.
- 🔔 إنذار فوري متعدد القنوات: قاعدة بيانات + Telegram + Email + بازر فعلي على العتاد.
- 💰 حاسبة توفير مالي وبيئي (تعريفة الكهرباء + معامل انبعاث CO₂).

---

## 🏗️ مخطط تدفق النظام

```
[Piezo Tiles / simulate_sensors.py] --MQTT--> [Mosquitto Broker] --> [ingest.py] --> [SQLite + CSV]
[WiFi RSSI Node]                    --MQTT-->        │
                                                      ▼
                                           [clean_data.py] --> [Parquet نظيف]
                                                      │
                ┌─────────────────────────────────────┼──────────────────────────────────┐
                ▼                                     ▼                                  ▼
   [train_occupancy_classifier.py]        [train_lstm_forecast.py]        [train_autoencoder_anomaly.py]
                └─────────────────────────────────────┬──────────────────────────────────┘
                                                       ▼
                                        [realtime_inference.py] ◄──MQTT── بيانات الحساسات الخام
                                            │                    │
                                     قرار تحكم بالأحمال     كشف شذوذ / تنبؤ
                                            │                    │
                                  [actuators/relay/*]   [alert_manager.py] → Telegram/Email/Buzzer
                                                       │
                                                [dashboard.py]
```

---

## 📂 هيكل المستودع

```
PowerStep/
├── esp32_main.ino                    # الفيرموير النهائي المدمج (طاقة + RSSI + إنذار)
├── simulate_sensors.py               # التوأم الرقمي — تجربة كاملة بدون بلاط فعلي
├── ingest.py                         # استقبال MQTT وتخزين في SQLite + نسخة CSV
├── fetch_data.py                     # سحب البيانات وتصديرها إلى Parquet
├── clean_data.py                     # تنظيف، فلترة، هندسة خصائص
├── train_occupancy_classifier.py     # ML: Random Forest / SVM لتصنيف الإشغال
├── train_lstm_forecast.py            # DL: LSTM للتنبؤ بالطاقة
├── train_autoencoder_anomaly.py      # DL: Autoencoder لكشف الشذوذ/الصيانة التنبؤية
├── realtime_inference.py             # محرك الاستدلال اللحظي (يربط كل النماذج بالتحكم)
├── alert_manager.py                  # محرك الإنذار (DB + Telegram + Email + Buzzer)
├── dashboard.py                      # لوحة التحكم الحية (Streamlit)
├── generate_qr.py                    # توليد رمز QR لعرض اللوحة على موبايل اللجنة
├── requirements.txt
├── models/                           # تُنشأ تلقائيًا بعد التدريب (.joblib / .keras / .json)
├── data/                             # تُنشأ تلقائيًا (energy_system.db, *.parquet, raw_backup.csv)
├── docs/
│   └── Smart_Energy_System_Roadmap.md   # خارطة الطريق التفصيلية الكاملة لكل مرحلة
└── README.md
```

---

## 🧰 التقنيات المستخدمة

| الفئة | الأدوات |
|---|---|
| العتاد | ESP32 (×2), أقراص بيزوكهربائية, قنطرة توحيد RB153, موسفيت IRF520N/ريليه, مكثفات فائقة, حساس تيار ACS712 |
| النقل | MQTT (Mosquitto) |
| التخزين | SQLite, CSV, Apache Parquet |
| تعلّم الآلة | scikit-learn (Random Forest, SVM) |
| التعلّم العميق | TensorFlow / Keras (LSTM, Autoencoder) |
| اللوحة | Streamlit, Plotly, streamlit-autorefresh |
| الإنذار | Telegram Bot API, SMTP (Email), MQTT |
| أخرى | qrcode, matplotlib, seaborn |
| اللغات | C++ (Arduino) · Python 3.10+ |

---

## 🚀 التشغيل السريع

```bash
# 1) الاستنساخ والتثبيت
git clone https://github.com/ahmedhhisham/PowerStep.git
cd PowerStep
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt --break-system-packages

# 2) تشغيل وسيط MQTT محليًا
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable --now mosquitto
# أو: docker run -it -p 1883:1883 eclipse-mosquitto

# 3) تشغيل خدمة التخزين
python ingest.py

# 4) تشغيل مصدر البيانات — اختر واحدًا
python simulate_sensors.py        # بدون أي عتاد فعلي (التوأم الرقمي)
# أو ارفع esp32_main.ino على العتاد الحقيقي عبر Arduino IDE

# 5) بعد تجميع بيانات كافية
python clean_data.py
python train_occupancy_classifier.py
python train_lstm_forecast.py
python train_autoencoder_anomaly.py

# 6) محرك الاستدلال اللحظي (يستدعي alert_manager تلقائيًا)
python realtime_inference.py

# 7) لوحة التحكم
streamlit run dashboard.py --server.address 0.0.0.0

# 8) رمز QR للعرض الحي
python generate_qr.py
```

### متغيرات البيئة (اختيارية — لقنوات الإنذار)

```bash
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."
export ALERT_EMAIL="you@example.com"
export SMTP_USER="..."
export SMTP_PASS="..."
```

---

## 🧪 تجربة المشروع بدون بلاط حقيقي

`simulate_sensors.py` ينشر بيانات صناعية على نفس مواضيع MQTT التي يستخدمها العتاد الحقيقي بالضبط، فتعمل كل الطبقات اللاحقة دون انتظار جاهزية البلاطة الميكانيكية. التفاصيل الكاملة (ومحاكاة هاردوير جزئية بزرار ضغط كبديل رخيص) في [`docs/Smart_Energy_System_Roadmap.md`](docs/Smart_Energy_System_Roadmap.md#3-تجربة-المشروع-بدون-بلاط-حقيقي-digital-twin--محاكاة-برمجية).

> 💡 **نصيحة ليوم العرض:** أبقِ `simulate_sensors.py` جاهزًا كخطة بديلة فورية لو واجه العتاد الحي أي مشكلة تقنية لحظة التحكيم.

---

## 📊 لوحة التحكم

تعرض اللوحة: التوليد والاستهلاك اللحظي (مقاييس دائرية)، نسبة الاكتفاء الذاتي، حالة شحن التخزين (SoC)، رسم بياني للتوليد التراكمي، خريطة كثافة حركة (RSSI Heat Strip)، تحكمًا يدويًا بالأحمال، حاسبة التوفير المالي/البيئي، وسجل التنبيهات.

> 📸 أضف لقطة شاشة من اللوحة هنا بعد أول تشغيل فعلي: `docs/images/dashboard.png`

---

## 🔔 نظام الإنذار

عند اكتشاف تسريب تيار (استهلاك رغم أن الحمل "OFF" رسميًا)، استهلاك زائد عن الطبيعي، أو انخفاض حرج في شحن التخزين، يُطلق `alert_manager.py` تنبيهًا فوريًا عبر: تسجيل في قاعدة البيانات (يظهر في اللوحة فورًا) + رسالة Telegram + بريد إلكتروني للحالات الحرجة + بازر فعلي على العتاد عبر MQTT.

---

## 🗺️ خارطة الطريق الكاملة

كل تفاصيل التخطيط، المشتريات، مخطط التوصيل، اختبار كل وحدة منفردة، والأكواد الكاملة لكل ملف مذكور أعلاه، موجودة خطوة بخطوة في: [`docs/Smart_Energy_System_Roadmap.md`](docs/Smart_Energy_System_Roadmap.md)

---

## 🤝 المساهمة

1. Fork المستودع.
2. أنشئ فرعًا جديدًا: `git checkout -b feature/my-feature`.
3. ارفع تعديلاتك: `git commit -m "وصف التعديل"`.
4. أنشئ Pull Request مع شرح واضح للتغيير.

---

## 🙌 شكر وتقدير

- كلية الذكاء الاصطناعي — جامعة كفر الشيخ الأهلية (KNU).
- مسابقة **RoboDam2026** على الفكرة الأساسية لحصاد الطاقة الحركية.
