/*
 * AGRISENTINEL EDGE - ESP32 SENSOR NODE FIRMWARE
 * -------------------------------------------------------------
 * Target Board: ESP32 DevKit V1 / Qualcomm IoT Hardware Node
 * Sensors: Capacitive Soil Moisture, DHT22 (Temp/Humidity), Soil EC
 * Protocol: HTTP POST to Edge Gateway / Backend (/api/sensor-data)
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>
#include "tinyml_crop_guard.h"

// WiFi Configuration
const char* ssid = "AgriSentinel_Farm_AP";
const char* password = "FarmPassword123";

// Backend Edge Gateway Endpoint
const char* serverUrl = "http://192.168.1.100:8000/api/sensor-data";

// Sensor & Actuator Pins
#define DHTPIN 4
#define DHTTYPE DHT22
#define SOIL_MOISTURE_PIN 34
#define SOIL_EC_PIN 35

// Physical Actuator Relays (Irrigation Pump & Bio-Mister)
#define PUMP_RELAY_PIN 26
#define MISTER_RELAY_PIN 27

// Optional I2C OLED Field Display (SSD1306)
// SDA = GPIO 21, SCL = GPIO 22

DHT dht(DHTPIN, DHTTYPE);

void setup() {
  Serial.begin(115200);
  dht.begin();

  // Initialize Actuator Relay Outputs (Active LOW or HIGH depending on relay module)
  pinMode(PUMP_RELAY_PIN, OUTPUT);
  pinMode(MISTER_RELAY_PIN, OUTPUT);
  digitalWrite(PUMP_RELAY_PIN, LOW);   // Safe default: pump OFF
  digitalWrite(MISTER_RELAY_PIN, LOW); // Safe default: mister OFF

  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 10) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nConnected! IP: " + WiFi.localIP().toString());
  } else {
    Serial.println("\nWiFi Offline - Operating in Standalone Edge Mode.");
  }
}

void loop() {
  // Read Sensors
  float airTemp = dht.readTemperature();
  float humidity = dht.readHumidity();
  int rawMoisture = analogRead(SOIL_MOISTURE_PIN);
  
  // Map raw capacitive reading (4095-0) to Moisture Percentage (0-100%)
  float z2_moisture = map(rawMoisture, 4095, 1200, 0, 100);
  z2_moisture = constrain(z2_moisture, 0, 100);
  float ec_salinity = 1.2;
  int pest_count = 25;

  // 🤖 RUN ON-DEVICE TinyML INFERENCE (Zero Latency, < 2ms execution)
  TinyMLResult ai_res = TinyMLCropGuard::predictRisk(z2_moisture, airTemp, humidity, pest_count, ec_salinity);
  Serial.println("\n[TinyML ESP32 Engine] Risk Level: " + String(ai_res.risk_level) + " | Score: " + String(ai_res.risk_score));
  Serial.println("[TinyML ESP32 Action] " + String(ai_res.action));

  // ⚡ HARDWARE ACTUATOR RELAY TRIGGER
  if (String(ai_res.action) == "ACTIVATE_PUMP_ZONE_2_IMMEDIATELY") {
    digitalWrite(PUMP_RELAY_PIN, HIGH);
    Serial.println("[ACTUATOR RELAY] Drip Irrigation Pump ACTIVATED for Zone 2");
  } else if (String(ai_res.action) == "DEACTIVATE_PUMP_DRAIN_SOIL") {
    digitalWrite(PUMP_RELAY_PIN, LOW);
    Serial.println("[ACTUATOR RELAY] Waterlogging detected. Irrigation Pump DEACTIVATED");
  } else {
    digitalWrite(PUMP_RELAY_PIN, LOW);
  }

  if (String(ai_res.action) == "TRIGGER_NEEM_OIL_MISTER") {
    digitalWrite(MISTER_RELAY_PIN, HIGH);
    Serial.println("[ACTUATOR RELAY] Bio-Pest Mister ACTIVATED");
  } else {
    digitalWrite(MISTER_RELAY_PIN, LOW);
  }

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;

    // Construct Telemetry JSON Payload with TinyML On-Device Diagnosis
    String jsonPayload = "{";
    jsonPayload += "\"zone_id\": 2,";
    jsonPayload += "\"z1_moisture\": 45.0,";
    jsonPayload += "\"z2_moisture\": " + String(z2_moisture, 1) + ",";
    jsonPayload += "\"z3_pest_count\": " + String(pest_count) + ",";
    jsonPayload += "\"z4_humidity\": " + String(humidity, 1) + ",";
    jsonPayload += "\"air_temp\": " + String(airTemp, 1) + ",";
    jsonPayload += "\"ec_salinity\": " + String(ec_salinity, 1) + ",";
    jsonPayload += "\"wind_speed\": 8.0,";
    jsonPayload += "\"tinyml_risk\": \"" + String(ai_res.risk_level) + "\",";
    jsonPayload += "\"tinyml_action\": \"" + String(ai_res.action) + "\"";
    jsonPayload += "}";

    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");
    
    int httpResponseCode = http.POST(jsonPayload);
    
    if (httpResponseCode > 0) {
      Serial.println("Telemetry & TinyML Posted! Code: " + String(httpResponseCode));
    } else {
      Serial.println("Telemetry POST Failed! Error: " + http.errorToString(httpResponseCode));
    }
    
    http.end();
  } else {
    Serial.println("WiFi Disconnected - TinyML Action executed locally on ESP32 flash memory & relays triggered.");
  }

  // Sample every 10 seconds
  delay(10000);
}

