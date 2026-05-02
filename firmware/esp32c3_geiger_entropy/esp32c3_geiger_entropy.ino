#include <Arduino.h>

const uint8_t GEIGER_PIN = 6;
const unsigned long REPORT_INTERVAL_MS = 10000;
const unsigned long DEBOUNCE_US = 1000;

volatile unsigned long totalPulses = 0;
volatile unsigned long intervalPulses = 0;
volatile unsigned long lastPulseUs = 0;
volatile bool pulsePending = false;
volatile unsigned long pendingPulseUs = 0;
volatile unsigned long pendingDeltaUs = 0;
volatile unsigned long droppedPulses = 0;

unsigned long lastReportMs = 0;

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

void printStatus(const char *typeName) {
  noInterrupts();
  const unsigned long total = totalPulses;
  const unsigned long dropped = droppedPulses;
  interrupts();

  Serial.print(F("{\"type\":\""));
  Serial.print(typeName);
  Serial.print(F("\",\"board\":\"esp32c3\",\"pin\":6,\"edge\":\"FALLING\",\"total\":"));
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
  printStatus("status");
}

void setup() {
  Serial.begin(115200);
  pinMode(GEIGER_PIN, INPUT);
  attachInterrupt(digitalPinToInterrupt(GEIGER_PIN), onPulse, FALLING);
  delay(500);
  lastReportMs = millis();
  printStatus("status");
}

void loop() {
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

  noInterrupts();
  if (pulsePending) {
    emitPulse = true;
    pulseUs = pendingPulseUs;
    deltaUs = pendingDeltaUs;
    total = totalPulses;
    pulsePending = false;
  }
  interrupts();

  if (emitPulse) {
    Serial.print(F("{\"type\":\"pulse\",\"t_us\":"));
    Serial.print(pulseUs);
    Serial.print(F(",\"dt_us\":"));
    Serial.print(deltaUs);
    Serial.print(F(",\"total\":"));
    Serial.print(total);
    Serial.println(F("}"));
  }

  const unsigned long nowMs = millis();
  if (nowMs - lastReportMs >= REPORT_INTERVAL_MS) {
    lastReportMs = nowMs;
    printReading();
  }
}

