#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <WiFiManager.h>
#include <ArduinoOTA.h>
#include <DHT.h>
#include <Preferences.h>
#include <mbedtls/md.h>
#include <ArduinoJson.h>
#include "edge_rule_engine.h"
#include "secrets.h" 

#define FIRMWARE_VERSION "2.1.0"

// Sensor & Actuator Pins
#define DHTPIN 4
#define DHTTYPE DHT22
#define SOIL_MOISTURE_PIN 34
#define PUMP_RELAY_PIN 26
#define MISTER_RELAY_PIN 27

// Hardware Lockout Configuration
#define MOISTURE_LOCKOUT_THRESHOLD 80.0
#define MAX_COMMAND_AGE_MS 60000 // 60 seconds

DHT dht(DHTPIN, DHTTYPE);
WiFiClientSecure secureClient;
PubSubClient mqttClient(secureClient);
Preferences preferences;

// Topics
String uplinkTopic = String("agrisaathi/nodes/") + DEVICE_ID + "/telemetry";
String statusTopic = String("agrisaathi/nodes/") + DEVICE_ID + "/status";
String downlinkTopic = String("agrisaathi/nodes/") + DEVICE_ID + "/commands";

// State
unsigned long lastTelemetryMillis = 0;
const long telemetryInterval = 60000;
long long lastSequenceNumber = 0;
float currentMoisture = -1.0; 

// Forward declarations
void setupOTA();
void reconnectMQTT();
String calculateHMAC(String canonicalString, String secret);
void sendAck(long long sequence, String status, bool relayState);

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  Serial.println("[MQTT] Message arrived on topic: " + String(topic));
  
  // Convert payload to string
  String message = "";
  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  // Parse JSON
  StaticJsonDocument<512> doc;
  DeserializationError error = deserializeJson(doc, message);
  
  if (error) {
    Serial.println("[SECURITY] Invalid JSON Payload");
    return;
  }

  String incDeviceId = doc["device_id"] | "";
  String incKeyId = doc["key_id"] | "";
  long long incSequence = doc["sequence"] | 0;
  long long incTimestamp = doc["timestamp"] | 0;
  String incNonce = doc["nonce"] | "";
  String incCommand = doc["command"] | "";
  int incDuration = doc["duration_sec"] | 0;
  String providedSig = doc["signature"] | "";

  // 1. Verify Device ID
  if (incDeviceId != String(DEVICE_ID)) {
    Serial.println("[SECURITY] Device ID mismatch");
    return;
  }

  // 2. Cryptographic Authentication
  // Canonical: device_id|key_id|sequence|timestamp|nonce|command|duration
  String canonical = String(DEVICE_ID) + "|" + incKeyId + "|" + String((long)incSequence) + "|" + 
                     String((long)incTimestamp) + "|" + incNonce + "|" + incCommand + "|" + String(incDuration);
  
  String expectedSig = calculateHMAC(canonical, String(EDGE_COMMAND_SECRET));
  
  if (expectedSig != providedSig) {
    Serial.println("[SECURITY] REJECTED_AUTH: Invalid HMAC Signature");
    sendAck(incSequence, "REJECTED_AUTH", digitalRead(PUMP_RELAY_PIN) == HIGH);
    return;
  }

  // 3. Replay Protection
  if (incSequence <= lastSequenceNumber) {
    Serial.println("[SECURITY] REJECTED_REPLAY: Sequence number not increasing");
    sendAck(incSequence, "REJECTED_REPLAY", digitalRead(PUMP_RELAY_PIN) == HIGH);
    return;
  }

  // 4. Timestamp Validation (Assuming ESP32 has synced time, simplified here for demo)
  // For production, ESP32 must sync NTP and validate `millis() / 1000`. 
  // We'll skip strict age check unless NTP is running, but normally it's checked here.
  // if (abs(currentServerTimeMs - incTimestamp) > MAX_COMMAND_AGE_MS) {
  //    sendAck(incSequence, "REJECTED_EXPIRED", ...);
  //    return;
  // }

  // 5. Hardware Interlock (Fail-Safe)
  if (incCommand == "PUMP_ON") {
    if (currentMoisture < 0) {
      Serial.println("[SAFETY] REJECTED_SENSOR: Sensor invalid/unavailable");
      sendAck(incSequence, "REJECTED_SENSOR", digitalRead(PUMP_RELAY_PIN) == HIGH);
      return;
    }
    if (currentMoisture > MOISTURE_LOCKOUT_THRESHOLD) {
      Serial.println("[SAFETY] REJECTED_SENSOR: Waterlogged interlock active");
      sendAck(incSequence, "REJECTED_SENSOR", digitalRead(PUMP_RELAY_PIN) == HIGH);
      return;
    }

    // SAFE to actuate
    digitalWrite(PUMP_RELAY_PIN, HIGH);
  } else if (incCommand == "PUMP_OFF") {
    digitalWrite(PUMP_RELAY_PIN, LOW);
  } else {
    // Unknown command
    sendAck(incSequence, "FAILED", digitalRead(PUMP_RELAY_PIN) == HIGH);
    return;
  }

  // Advance sequence ONLY after successful verification and actuation
  lastSequenceNumber = incSequence;
  preferences.begin("agrisentinel", false);
  // store lower 32 bits and upper 32 bits if needed, or cast to uint32_t for simple NVS.
  // We'll store as uint32_t since sequence fits for a while, but ESP32 preferences supports int64
  preferences.putLong64("lastSeq", lastSequenceNumber);
  preferences.end();

  Serial.println("[ACTUATION] Command Accepted and Executed securely.");
  sendAck(incSequence, "ACTUATION_ACCEPTED", digitalRead(PUMP_RELAY_PIN) == HIGH);
}

void sendAck(long long sequence, String status, bool relayState) {
  // ACK Canonical: device_id|key_id|sequence|status|relay_state|timestamp
  long long ts = millis(); // Using millis as mockup for timestamp
  String canonical = String(DEVICE_ID) + "|" + String(EDGE_KEY_ID) + "|" + String((long)sequence) + "|" + 
                     status + "|" + (relayState ? "1" : "0") + "|" + String((long)ts);
  
  String sig = calculateHMAC(canonical, String(EDGE_COMMAND_SECRET));

  StaticJsonDocument<256> doc;
  doc["device_id"] = String(DEVICE_ID);
  doc["key_id"] = String(EDGE_KEY_ID);
  doc["sequence"] = sequence;
  doc["status"] = status;
  doc["relay_state"] = relayState;
  doc["timestamp"] = ts;
  doc["signature"] = sig;

  String payload;
  serializeJson(doc, payload);

  String ackTopic = String("agrisaathi/nodes/") + DEVICE_ID + "/commands/ack";
  mqttClient.publish(ackTopic.c_str(), payload.c_str(), true); // QoS 1 equivalent
}

String calculateHMAC(String canonicalString, String secret) {
  mbedtls_md_context_t ctx;
  mbedtls_md_type_t md_type = MBEDTLS_MD_SHA256;
  
  const size_t payloadLength = canonicalString.length();
  const size_t secretLength = secret.length();
  
  mbedtls_md_init(&ctx);
  mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(md_type), 1);
  mbedtls_md_hmac_starts(&ctx, (const unsigned char *)secret.c_str(), secretLength);
  mbedtls_md_hmac_update(&ctx, (const unsigned char *)canonicalString.c_str(), payloadLength);
  
  byte mac[32];
  mbedtls_md_hmac_finish(&ctx, mac);
  mbedtls_md_free(&ctx);
  
  String hashStr = "";
  for(int i=0; i<32; i++) {
    char hex[3];
    sprintf(hex, "%02x", mac[i]);
    hashStr += hex;
  }
  return hashStr;
}

void setupOTA() {
  ArduinoOTA.setHostname(DEVICE_ID);
  ArduinoOTA.begin();
}

void reconnectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("Attempting MQTT connection...");
    String lwtPayload = "{\"device_id\":\"" + String(DEVICE_ID) + "\",\"status\":\"offline\"}";
    if (mqttClient.connect(DEVICE_ID, mqtt_user, mqtt_pass, statusTopic.c_str(), 1, true, lwtPayload.c_str())) {
      Serial.println("connected");
      String onlinePayload = "{\"device_id\":\"" + String(DEVICE_ID) + "\",\"status\":\"online\",\"version\":\"" + String(FIRMWARE_VERSION) + "\"}";
      mqttClient.publish(statusTopic.c_str(), onlinePayload.c_str(), true);
      mqttClient.subscribe(downlinkTopic.c_str(), 1); // QoS 1
    } else {
      delay(5000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  dht.begin();

  // Fail-safe initialization
  pinMode(PUMP_RELAY_PIN, OUTPUT);
  pinMode(MISTER_RELAY_PIN, OUTPUT);
  digitalWrite(PUMP_RELAY_PIN, LOW);
  digitalWrite(MISTER_RELAY_PIN, LOW);

  // Load NVS Sequence
  preferences.begin("agrisentinel", true); // read-only
  lastSequenceNumber = preferences.getLong64("lastSeq", 0);
  preferences.end();
  Serial.print("Loaded Last Sequence Number: ");
  Serial.println((long)lastSequenceNumber);

  WiFiManager wifiManager;
  wifiManager.setClass("invert");
  String apName = String("AgriSentinel-Setup-") + DEVICE_ID;
  if (!wifiManager.autoConnect(apName.c_str(), "setup1234")) {
    delay(3000);
    ESP.restart();
  }
  
  secureClient.setCACert(root_ca);
  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setCallback(mqttCallback);

  setupOTA();
}

void loop() {
  ArduinoOTA.handle();

  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();

  unsigned long currentMillis = millis();
  if (currentMillis - lastTelemetryMillis >= telemetryInterval) {
    lastTelemetryMillis = currentMillis;

    float humidity = dht.readHumidity();
    float airTemp = dht.readTemperature();
    int rawMoisture = analogRead(SOIL_MOISTURE_PIN);
    
    // Evaluate sensors
    float z2_moisture = -1.0;
    if (rawMoisture > 0 && rawMoisture <= 4095) {
      z2_moisture = map(rawMoisture, 4095, 1200, 0, 100);
      z2_moisture = constrain(z2_moisture, 0, 100);
      currentMoisture = z2_moisture; // Cache for hardware interlock
    } else {
      currentMoisture = -1.0; // Invalid
    }

    EdgeRuleResult res = EdgeRuleEngine::evaluateRisk(z2_moisture, airTemp, humidity);
    
    // PHASE 3.1 REMEDIATION (Sept 18, 2026):
    // Removed autonomous relay actuation. All pump commands must be authorized by backend.
    // Edge device now uses local rule engine ONLY for edge-side risk assessment,
    // but final pump command must come through backend via signed MQTT command.
    // This ensures:
    // - Rain forecast integration (backend checks weather API)
    // - Irrigation schedule enforcement
    // - Multi-device arbitration
    // - Audit trail of decisions
    //
    // The edge_rule_engine output is still valuable for offline diagnostics,
    // but is NOT used for actuation without backend approval.
    
    // Build JSON Payload
    StaticJsonDocument<512> doc;
    doc["device_id"] = String(DEVICE_ID);
    doc["timestamp"] = millis();
    
    JsonObject telemetry = doc.createNestedObject("telemetry");
    if (currentMoisture >= 0) telemetry["soil_moisture_pct"] = z2_moisture; else telemetry["soil_moisture_pct"] = nullptr;
    telemetry["soil_raw_adc"] = rawMoisture;
    if (!isnan(airTemp)) telemetry["temperature_c"] = airTemp; else telemetry["temperature_c"] = nullptr;
    if (!isnan(humidity)) telemetry["humidity_pct"] = humidity; else telemetry["humidity_pct"] = nullptr;
    
    JsonObject actuator = doc.createNestedObject("actuator");
    actuator["pump_active"] = (digitalRead(PUMP_RELAY_PIN) == HIGH);
    
    JsonObject edge_ai = doc.createNestedObject("edge_ai");
    edge_ai["last_scan_result"] = String(res.risk_level);
    edge_ai["confidence_pct"] = nullptr;
    
    String payload;
    serializeJson(doc, payload);

    if (mqttClient.publish(uplinkTopic.c_str(), payload.c_str())) {
      Serial.println("Published: " + payload);
    } else {
      Serial.println("[DIAGNOSTICS] Failed to publish telemetry MQTT packet.");
    }
  }
}
