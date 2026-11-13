#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>

const char* WIFI_SSID     = "wifi_bro";
const char* WIFI_PASSWORD = "pass_cua_bro";
const char* SERVER_URL    = "http://ipv4_trong_ipconfig_cua_bro:8000";
const char* DEVICE_CODE   = "ESP32-01";

const int SOIL_DRY = 4095;
const int SOIL_WET = 1400;

#define PIN_DHT    4
#define PIN_SOIL   34
#define PIN_RELAY  26

const unsigned long SEND_INTERVAL    = 10000;
const unsigned long COMMAND_INTERVAL = 3000;
const unsigned long MAX_PUMP_MS      = 300000;

DHT dht(PIN_DHT, DHT11);

enum Phase { IDLE, PULSE, SOAK };

struct Job {
  Phase         phase = IDLE;
  long          commandId = 0;
  unsigned long maxMs = 0;
  unsigned long pumpedMs = 0;
  unsigned long pulseMs = 0;
  unsigned long soakMs = 0;
  float         stopAt = -1;
  unsigned long phaseStart = 0;
  unsigned long phaseEnd = 0;
  int           pulses = 0;
} job;

unsigned long lastSend = 0, lastCommand = 0;

int readSoilMedian() {
  const int N = 21;
  int v[N];
  for (int i = 0; i < N; i++) { v[i] = analogRead(PIN_SOIL); delay(3); }
  for (int i = 1; i < N; i++) {
    int k = v[i], j = i - 1;
    while (j >= 0 && v[j] > k) { v[j + 1] = v[j]; j--; }
    v[j + 1] = k;
  }
  return v[N / 2];
}

int readSoilSmooth() {
  static float smooth = -1;
  int m = readSoilMedian();
  smooth = (smooth < 0) ? m : smooth * 0.7 + m * 0.3;
  return (int)smooth;
}

float soilPercent(int raw) {
  float p = (float)(SOIL_DRY - raw) * 100.0 / (SOIL_DRY - SOIL_WET);
  return constrain(p, 0, 100);
}

void readDHT(float &temp, float &hum) {
  for (int i = 0; i < 3; i++) {
    temp = dht.readTemperature();
    hum  = dht.readHumidity();
    if (!isnan(temp) && !isnan(hum)) return;
    delay(2000);
  }
  Serial.println("[DHT11] Khong doc duoc -> kiem tra day DATA (D4), VCC, GND");
}

void ensureWiFi() {
  static unsigned long lastTry = 0;
  static bool wasConnected = false;
  bool connected = WiFi.status() == WL_CONNECTED;
  if (connected && !wasConnected)
    Serial.printf("[WIFI] Da ket noi, IP ESP32: %s\n", WiFi.localIP().toString().c_str());
  wasConnected = connected;
  if (connected) return;
  if (lastTry != 0 && millis() - lastTry < 10000) return;
  lastTry = millis();
  Serial.printf("[WIFI] Dang ket noi '%s' ...\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
}

int postJson(const String& path, const String& body, String* response) {
  if (WiFi.status() != WL_CONNECTED) return -1;
  HTTPClient http;
  http.begin(String(SERVER_URL) + path);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(4000);
  int code = http.POST(body);
  if (response && code > 0) *response = http.getString();
  http.end();
  return code;
}

void relay(bool on) { digitalWrite(PIN_RELAY, on ? HIGH : LOW); }

void startPulse() {
  unsigned long left = job.maxMs - job.pumpedMs;
  unsigned long len = min(job.pulseMs, left);
  job.phase = PULSE;
  job.phaseStart = millis();
  job.phaseEnd = job.phaseStart + len;
  job.pulses++;
  relay(true);
  Serial.printf("[BOM] Nhip %d: bom %lu ms (da bom %lu/%lu ms)\n", job.pulses, len, job.pumpedMs, job.maxMs);
}

void finishJob(const char* reason, float finalSoil) {
  if (job.phase == PULSE) job.pumpedMs += millis() - job.phaseStart;
  relay(false);
  job.phase = IDLE;
  int pumpedSec = (job.pumpedMs + 500) / 1000;
  Serial.printf("[BOM] XONG: %s | bom that %d giay | dat %.1f%%\n", reason, pumpedSec, finalSoil);

  if (job.commandId > 0) {
    JsonDocument doc;
    doc["device_code"] = DEVICE_CODE;
    doc["command_id"]  = job.commandId;
    doc["pumped_sec"]  = pumpedSec;
    if (finalSoil >= 0) doc["final_moisture"] = round(finalSoil * 10) / 10.0;
    doc["reason"] = reason;
    String body; serializeJson(doc, body);
    for (int i = 0; i < 3; i++) {
      int code = postJson("/api/device/pump-done", body, nullptr);
      if (code == 200) { Serial.println("[API] Da bao ket qua bom"); break; }
      delay(1000);
    }
  }
  job.commandId = 0;
}

void startJob(long commandId, unsigned long maxMs, float stopAt,
              unsigned long pulseMs, unsigned long soakMs) {
  if (job.phase != IDLE) finishJob("bi thay boi lenh moi", -1);
  if (maxMs == 0) return;
  job.commandId = commandId;
  job.maxMs = min(maxMs, MAX_PUMP_MS);
  job.pumpedMs = 0;
  job.stopAt = stopAt;
  job.pulseMs = (stopAt < 0 || pulseMs == 0) ? job.maxMs : pulseMs;
  job.soakMs = soakMs;
  job.pulses = 0;

  if (stopAt >= 0) {
    float soil = soilPercent(readSoilMedian());
    Serial.printf("[BOM] Tuoi den %.0f%% (toi da %lu giay), dat hien %.1f%%\n", stopAt, job.maxMs / 1000, soil);
    if (soil >= stopAt) { finishJob("dat da du am truoc khi bom", soil); return; }
  }
  startPulse();
}

void pumpTick() {
  if (job.phase == IDLE) return;
  unsigned long now = millis();
  if ((long)(now - job.phaseEnd) < 0) return;

  if (job.phase == PULSE) {
    relay(false);
    job.pumpedMs += now - job.phaseStart;
    if (job.pumpedMs + 200 >= job.maxMs) {
      float soil = soilPercent(readSoilMedian());
      finishJob(job.stopAt < 0 ? "du so giay bom tay" : "het thoi gian toi da", soil);
      return;
    }
    job.phase = SOAK;
    job.phaseEnd = now + job.soakMs;
    Serial.printf("[BOM] Cho tham %lu ms...\n", job.soakMs);
    return;
  }

  float soil = soilPercent(readSoilMedian());
  Serial.printf("[BOM] Sau nhip %d: dat %.1f%% / muc tieu %.0f%%\n", job.pulses, soil, job.stopAt);
  if (soil >= job.stopAt) finishJob("dat da dat muc tieu", soil);
  else startPulse();
}

void sendReading(int raw, float soil, float temp, float hum) {
  JsonDocument doc;
  doc["device_code"]   = DEVICE_CODE;
  doc["soil_raw"]      = raw;
  doc["soil_moisture"] = round(soil * 10) / 10.0;
  if (!isnan(temp)) doc["air_temp"]     = temp;
  if (!isnan(hum))  doc["air_humidity"] = hum;
  String body, res; serializeJson(doc, body);
  int code = postJson("/api/device/readings", body, &res);
  if (code == 200) Serial.printf("[API] Gui OK: %s\n", res.c_str());
  else             Serial.printf("[API] Gui loi: %d\n", code);
}

void pollCommand() {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.begin(String(SERVER_URL) + "/api/device/command?device_code=" + DEVICE_CODE +
             "&pump_on=" + (job.phase == PULSE ? "true" : "false"));
  http.setTimeout(3000);
  int code = http.GET();
  if (code != 200) { http.end(); return; }

  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, http.getString());
  http.end();
  if (err) return;

  const char* action = doc["action"] | "NONE";
  if (strcmp(action, "ON") == 0) {
    startJob(doc["command_id"] | 0L,
             (unsigned long)(doc["duration_sec"] | 0) * 1000UL,
             doc["stop_at"] | -1.0f,
             (unsigned long)(doc["pulse_sec"] | 0) * 1000UL,
             (unsigned long)(doc["soak_sec"] | 0) * 1000UL);
  } else if (strcmp(action, "OFF") == 0 && job.phase != IDLE) {
    finishJob("tat tu web", soilPercent(readSoilMedian()));
  }
}

void setup() {
  Serial.begin(115200);
  delay(300);
  pinMode(PIN_RELAY, OUTPUT);
  relay(false);
  analogReadResolution(12);
  analogSetPinAttenuation(PIN_SOIL, ADC_11db);
  dht.begin();
  delay(2000);

  Serial.println("\n=== ENV-07 ESP32 ===");
  Serial.printf("Backend: %s | Thiet bi: %s\n", SERVER_URL, DEVICE_CODE);
  ensureWiFi();
}

void loop() {
  pumpTick();
  ensureWiFi();

  unsigned long now = millis();

  if (now - lastCommand >= COMMAND_INTERVAL) {
    lastCommand = now;
    pollCommand();
  }

  if (job.phase == IDLE && now - lastSend >= SEND_INTERVAL) {
    lastSend = now;
    int raw    = readSoilSmooth();
    float soil = soilPercent(raw);
    float temp, hum;
    readDHT(temp, hum);
    Serial.printf("[DO] Dat %.1f%% (ADC %d) | %.1f C | Am KK %.0f%%\n", soil, raw, temp, hum);
    sendReading(raw, soil, temp, hum);
  }

  delay(20);
}