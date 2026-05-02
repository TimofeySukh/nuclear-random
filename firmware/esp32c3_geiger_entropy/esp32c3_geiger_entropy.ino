#include <Arduino.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

#include "secrets.h"

const uint8_t GEIGER_PIN = 6;
const unsigned long REPORT_INTERVAL_MS = 10000;
const unsigned long DEBOUNCE_US = 1000;
const unsigned long WIFI_RETRY_MS = 5000;
const unsigned long HTTP_TIMEOUT_MS = 5000;

volatile unsigned long totalPulses = 0;
volatile unsigned long intervalPulses = 0;
volatile unsigned long lastPulseUs = 0;
volatile bool pulsePending = false;
volatile unsigned long pendingPulseUs = 0;
volatile unsigned long pendingDeltaUs = 0;
volatile unsigned long droppedPulses = 0;

unsigned long lastReportMs = 0;
unsigned long lastWifiAttemptMs = 0;
unsigned long sequence = 0;

void IRAM_ATTR onPulse() {
  const unsigned long nowUs = micros();
  const unsigned long deltaUs = nowUs - lastPulseUs;
  if (deltaUs < DEBOUNCE_US) {
    return;
  }

  lastPulseUs = nowUs;
  totalPulses++;
  intervalPulses++;

  if (pulsePending) {
    droppedPulses++;
    return;
  }

  pendingPulseUs = nowUs;
  pendingDeltaUs = deltaUs;
  pulsePending = true;
}

void connectWifi() {
  if (WiFi.status() == WL_CONNECTED) {
    return;
  }

  const unsigned long nowMs = millis();
  if (nowMs - lastWifiAttemptMs < WIFI_RETRY_MS) {
    return;
  }

  lastWifiAttemptMs = nowMs;
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.println(F("{\"type\":\"wifi_connecting\"}"));
}

String makePulsePayload(unsigned long pulseUs, unsigned long deltaUs, unsigned long total, unsigned long dropped) {
  sequence++;

  String payload = "{";
  payload += "\"source\":\"esp32c3_gpio6_wifi\",";
  payload += "\"sequence\":";
  payload += sequence;
  payload += ",\"device_time_us\":";
  payload += pulseUs;
  payload += ",\"dt_us\":";
  payload += deltaUs;
  payload += ",\"total\":";
  payload += total;
  payload += ",\"dropped\":";
  payload += dropped;
  payload += "}";
  return payload;
}

bool postPulse(const String &payload) {
  if (WiFi.status() != WL_CONNECTED) {
    return false;
  }

  WiFiClientSecure client;
  client.setInsecure();

  HTTPClient http;
  http.setTimeout(HTTP_TIMEOUT_MS);
  if (!http.begin(client, INGEST_URL)) {
    return false;
  }

  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Nuclear-Random-Token", INGEST_TOKEN);
  const int status = http.POST(payload);
  http.end();

  Serial.print(F("{\"type\":\"ingest\",\"status\":"));
  Serial.print(status);
  Serial.println(F("}"));

  return status >= 200 && status < 300;
}

void printStatus(const char *typeName) {
  noInterrupts();
  const unsigned long total = totalPulses;
  const unsigned long dropped = droppedPulses;
  interrupts();

  Serial.print(F("{\"type\":\""));
  Serial.print(typeName);
  Serial.print(F("\",\"board\":\"esp32c3\",\"pin\":6,\"edge\":\"FALLING\",\"wifi\":"));
  Serial.print(WiFi.status() == WL_CONNECTED ? F("true") : F("false"));
  Serial.print(F(",\"total\":"));
  Serial.print(total);
  Serial.print(F(",\"dropped\":"));
  Serial.print(dropped);
  Serial.println(F("}"));
}

void printReading() {
  noInterrupts();
  const unsigned long interval = intervalPulses;
  intervalPulses = 0;
  const unsigned long total = totalPulses;
  const unsigned long dropped = droppedPulses;
  interrupts();

  const float cpm = interval * (60000.0 / REPORT_INTERVAL_MS);
  Serial.print(F("{\"type\":\"reading\",\"counts\":"));
  Serial.print(interval);
  Serial.print(F(",\"cpm\":"));
  Serial.print(cpm, 2);
  Serial.print(F(",\"total\":"));
  Serial.print(total);
  Serial.print(F(",\"dropped\":"));
  Serial.print(dropped);
  Serial.print(F(",\"wifi\":"));
  Serial.print(WiFi.status() == WL_CONNECTED ? F("true") : F("false"));
  Serial.println(F("}"));
}

void resetCounters() {
  noInterrupts();
  totalPulses = 0;
  intervalPulses = 0;
  lastPulseUs = 0;
  pulsePending = false;
  pendingPulseUs = 0;
  pendingDeltaUs = 0;
  droppedPulses = 0;
  interrupts();
  sequence = 0;
  printStatus("status");
}

void setup() {
  Serial.begin(115200);
  pinMode(GEIGER_PIN, INPUT);
  attachInterrupt(digitalPinToInterrupt(GEIGER_PIN), onPulse, FALLING);
  delay(500);
  lastReportMs = millis();
  connectWifi();
  printStatus("status");
}

void loop() {
  connectWifi();

  if (Serial.available() > 0) {
    const String command = Serial.readStringUntil('\n');
    if (command == "RESET" || command == "RESET\r") {
      resetCounters();
    } else if (command == "STATUS" || command == "STATUS\r") {
      printStatus("status");
    }
  }

  bool emitPulse = false;
  unsigned long pulseUs = 0;
  unsigned long deltaUs = 0;
  unsigned long total = 0;
  unsigned long dropped = 0;

  noInterrupts();
  if (pulsePending) {
    emitPulse = true;
    pulseUs = pendingPulseUs;
    deltaUs = pendingDeltaUs;
    total = totalPulses;
    dropped = droppedPulses;
    pulsePending = false;
  }
  interrupts();

  if (emitPulse) {
    const String payload = makePulsePayload(pulseUs, deltaUs, total, dropped);
    Serial.println(payload);
    if (!postPulse(payload)) {
      droppedPulses++;
    }
  }

  const unsigned long nowMs = millis();
  if (nowMs - lastReportMs >= REPORT_INTERVAL_MS) {
    lastReportMs = nowMs;
    printReading();
  }
}

