/*
  ============================================================================
  esp32_main.ino

  المكتبات المطلوبة (Arduino IDE > Library Manager):
    - PubSubClient   by Nick O'Leary
    - ArduinoJson    by Benoit Blanchon (الإصدار 6.x)
    - WiFi.h         (مدمجة مع حزمة ESP32 — أضف رابط Boards Manager:
      https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json)

  قبل الرفع، عدّل حتمًا: WIFI_SSID / WIFI_PASSWORD / MQTT_BROKER / TILE_ID / NODE_ID
  وثوابت المعايرة في نهاية هذا القسم بعد قياسات فعلية بالمالتيميتر/الأوسيلوسكوب.
  ============================================================================
*/

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <time.h>
#include <math.h>

// ---------------------- تفعيل/تعطيل الوظائف حسب دور القطعة --------------------
#define ENABLE_ENERGY_HARVESTING 1   // 0 على عقدة RSSI المستقلة
#define ENABLE_OCCUPANCY_SENSING 1   // 0 على عقدة الطاقة المستقلة
#define ENABLE_CURRENT_SENSOR    0   // 1 فقط لو ACS712 موصول فعليًا

// ------------------------------ إعدادات الشبكة ------------------------------
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* MQTT_BROKER   = "192.168.1.100";  
const int   MQTT_PORT     = 1883;

const char* TILE_ID = "tile_1";            // يطابق TILE_IDS في simulate_sensors.py
const char* NODE_ID = "corridor_node_1";   // يطابق NODE_IDS في simulate_sensors.py

// أسماء المواضيع — مطابقة تمامًا لما يتوقعه ingest.py و realtime_inference.py
String       TOPIC_ENERGY   = "energy/tiles/" + String(TILE_ID) + "/telemetry";
String       TOPIC_RSSI     = "occupancy/rssi/" + String(NODE_ID) + "/telemetry";
const char*  TOPIC_RELAY_CMD = "actuators/relay/corridor_light/cmd";
const char*  TOPIC_ALERTS    = "alerts/system";

// ---------------------------- تعريف الأطراف (Pinout) ------------------------
const int PIEZO_PIN  = 34;  
const int ACS712_PIN = 35;  
const int RELAY_PIN  = 26;   
const int BUZZER_PIN = 27;
const int STATUS_LED = 2;    

// -------------------------- ثوابت المعايرة (حدّثها بعد القياس الفعلي) --------
const float STEP_DETECT_THRESHOLD_V  = 1.2;   
const unsigned long STEP_DEBOUNCE_MS = 150;   
const float ENERGY_WH_PER_STEP       = 0.0006; 
const float ACS712_SENSITIVITY_V_PER_A = 0.100;  
const float ACS712_ZERO_OFFSET_V     = 1.65;
const float BUS_VOLTAGE_V            = 12.0;   

const unsigned long PUBLISH_INTERVAL_MS = 5000; // نفس فترة النشر في simulate_sensors.py

// -------------------------------- المتغيرات العامة ---------------------------
WiFiClient   espClient;
PubSubClient mqttClient(espClient);

unsigned long lastStepTime     = 0;
unsigned int  stepCount        = 0;
unsigned long lastPublishTime  = 0;

// ============================================================================
void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("جارٍ الاتصال بالواي فاي");
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");
  }
  Serial.println("\nمتصل. IP: " + WiFi.localIP().toString());

  // مزامنة الوقت عبر NTP لإنتاج طابع زمني ISO8601 متوافق مع simulate_sensors.py
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
}

String isoTimestamp() {
  time_t now = time(nullptr);
  struct tm timeinfo;
  gmtime_r(&now, &timeinfo);
  char buf[25];
  strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
  return String(buf);
}

// عند وصول أمر تحكم بالريليه أو تنبيه من alert_manager.py
void onMqttMessage(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
  String t = String(topic);

  if (t == TOPIC_RELAY_CMD) {
    digitalWrite(RELAY_PIN, msg == "ON" ? HIGH : LOW);
    Serial.println("[RELAY] " + msg);
  } else if (t == TOPIC_ALERTS) {
    if (msg.indexOf("\"severity\":\"high\"") >= 0) {
      Serial.println("[ALERT] تنبيه حرج — تشغيل البازر");
      digitalWrite(BUZZER_PIN, HIGH);
      delay(1500);
      digitalWrite(BUZZER_PIN, LOW);
    }
  }
}

void connectMqtt() {
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(onMqttMessage);
  // معرّف فريد لكل قطعة حتى لا تتعارض عند تشغيل عقدتين معًا (طاقة + RSSI)
  String clientId = "esp32_" + String(TILE_ID) + "_" + String(NODE_ID);

  while (!mqttClient.connected()) {
    Serial.print("جارٍ الاتصال بخادم MQTT...");
    if (mqttClient.connect(clientId.c_str())) {
      Serial.println("تم الاتصال");
      mqttClient.subscribe(TOPIC_RELAY_CMD);
      mqttClient.subscribe(TOPIC_ALERTS);
      digitalWrite(STATUS_LED, HIGH);
    } else {
      Serial.printf("فشل rc=%d، إعادة المحاولة خلال 2 ثانية\n", mqttClient.state());
      digitalWrite(STATUS_LED, LOW);
      delay(2000);
    }
  }
}

// ------------------------- حصاد الطاقة: عدّ الخطوات لحظيًا -------------------
void sampleEnergyHarvesting() {
  int raw = analogRead(PIEZO_PIN);
  float voltage = (raw / 4095.0) * 3.3 * 2.0;  

  unsigned long now = millis();
  if (voltage >= STEP_DETECT_THRESHOLD_V && (now - lastStepTime) > STEP_DEBOUNCE_MS) {
    stepCount++;
    lastStepTime = now;
  }
}

void publishEnergyTelemetry() {
  float energyWhDelta = stepCount * ENERGY_WH_PER_STEP;
  float intervalHours = PUBLISH_INTERVAL_MS / 3600000.0;
  float powerMw = (intervalHours > 0) ? (energyWhDelta / intervalHours) * 1000.0 : 0;

  StaticJsonDocument<256> doc;
  doc["tile_id"]         = TILE_ID;
  doc["steps"]           = stepCount;
  doc["power_mw"]        = round(powerMw * 100) / 100.0;
  doc["energy_wh_delta"] = energyWhDelta;

#if ENABLE_CURRENT_SENSOR
  int   rawCurrent = analogRead(ACS712_PIN);
  float sensorV    = (rawCurrent / 4095.0) * 3.3;
  float current    = (sensorV - ACS712_ZERO_OFFSET_V) / ACS712_SENSITIVITY_V_PER_A;
  doc["consumption_mw"] = round(fabsf(current) * BUS_VOLTAGE_V * 1000 * 100) / 100.0;
#endif

  doc["ts"] = isoTimestamp();

  char buffer[256];
  serializeJson(doc, buffer, sizeof(buffer));
  mqttClient.publish(TOPIC_ENERGY.c_str(), buffer);

  stepCount = 0;   
}

// --------------------------- استشعار الإشغال عبر RSSI ------------------------
void publishOccupancyTelemetry() {
  long rssi = WiFi.RSSI();  

  StaticJsonDocument<160> doc;
  doc["node_id"] = NODE_ID;
  doc["rssi"]    = rssi;
  doc["ts"]      = isoTimestamp();

  char buffer[160];
  serializeJson(doc, buffer, sizeof(buffer));
  mqttClient.publish(TOPIC_RSSI.c_str(), buffer);
}

// ============================================================================
void setup() {
  Serial.begin(115200);
  pinMode(RELAY_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(STATUS_LED, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);
  digitalWrite(BUZZER_PIN, LOW);
  analogReadResolution(12);   

  connectWiFi();
  connectMqtt();
}

void loop() {
  if (!mqttClient.connected()) connectMqtt();
  mqttClient.loop();

#if ENABLE_ENERGY_HARVESTING
  sampleEnergyHarvesting();
#endif

  unsigned long now = millis();
  if (now - lastPublishTime >= PUBLISH_INTERVAL_MS) {
    lastPublishTime = now;
#if ENABLE_ENERGY_HARVESTING
    publishEnergyTelemetry();
#endif
#if ENABLE_OCCUPANCY_SENSING
    publishOccupancyTelemetry();
#endif
  }
}
