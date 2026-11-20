/*
  SANKET PTT ESP32 AUDIO KIT V2.2 — TWO-WAY WSS VERSION
  Target: classic ESP32 Audio Kit V2.2 / ES8388
  Channel: virtual
  Audio: 12 kHz, mono, signed 16-bit PCM
  PTT: GPIO34 (external 10K pull-up required; GPIO34 has no internal pull-up)

  Transport matches SanketPTT browser: MQTT 3.1.1 over WSS, path /mqtt.
  Default relay: public.cloud.shiftr.io:443 (public demo only).
  This is a prototype; compile and test on the exact board before deployment.
*/

#include <Arduino.h>
#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <WebServer.h>
#include <vector>
#include <time.h>
#include "AudioTools.h"
#include "AudioLibs/I2SCodecStream.h"

// ---------------- HARDWARE / AUDIO ----------------
#define PTT_PIN 34
#define AMP_ENABLE 21
#define STATUS_LED 22
#define AUDIO_RATE 12000
#define AUDIO_SAMPLES 600
#define AUDIO_BYTES (AUDIO_SAMPLES * 2)
#define RX_QUEUE_DEPTH 8

// ---------------- WIFI / RADIO ----------------
const char* WIFI_DEFAULT = "Home2G2";
const char* PREFIX = "ptt-radio-66ab9178/";
const char* CHANNEL = "virtual";
const char* DEVICE_DEFAULT = "SANKET-ESP32";

// Must match the relay selected by the browser client.
// Default is the first relay in the SanketPTT website.
const bool USE_EMQX_RELAY = false;
const char* SHIFTR_HOST = "public.cloud.shiftr.io";
const uint16_t SHIFTR_PORT = 443;
const char* SHIFTR_PATH = "/mqtt";
const char* SHIFTR_USER = "public";
const char* SHIFTR_PASS = "public";

// ---------------- OBJECTS ----------------
I2SCodecStream audio(AudioKitEs8388V2);
WebSocketsClient ws;
Preferences prefs;
WebServer server(80);

String wifiSSID1, wifiPASS1, wifiSSID2, wifiPASS2;
String deviceID, deviceName = DEVICE_DEFAULT, addressee = "ALL";
String configPIN, floorID, floorName;
String tPresenceSelf, tPresenceWildcard, tFloor, tAudio;

struct RxFrame { uint16_t length; uint8_t data[AUDIO_BYTES]; };
QueueHandle_t rxQueue = nullptr;

bool audioReady = false, wsConnected = false, mqttConnected = false;
bool joined = false, pttDown = false, floorGranted = false;
bool claimPending = false, portalMode = false;
uint32_t claimTime = 0, lastHeartbeat = 0, lastPresence = 0;
uint64_t floorTimestamp = 0;
uint32_t lastPing = 0, lastStatusLog = 0;
bool clockReady = false;
uint16_t mqttPacketId = 1;
uint8_t mqttRx[4096];
size_t mqttRxLen = 0;

// ---------------- TOPICS / MQTT ENCODING ----------------
String makeDeviceID() {
  uint64_t mac = ESP.getEfuseMac();
  char b[12];
  snprintf(b, sizeof(b), "%08lX", (uint32_t)(mac & 0xFFFFFFFF));
  return String(b);
}
String topic(const String& suffix) {
  return String(PREFIX) + CHANNEL + "/" + suffix;
}
void appendMqttString(std::vector<uint8_t>& b, const String& s) {
  uint16_t n = (uint16_t)s.length();
  b.push_back((uint8_t)(n >> 8)); b.push_back((uint8_t)n);
  for (size_t i = 0; i < s.length(); ++i) b.push_back((uint8_t)s[i]);
}
size_t encodeRemaining(uint8_t* out, size_t value) {
  size_t n = 0;
  do {
    uint8_t digit = value % 128; value /= 128;
    if (value) digit |= 0x80;
    out[n++] = digit;
  } while (value && n < 4);
  return n;
}
bool sendMqtt(const std::vector<uint8_t>& packet) {
  return wsConnected && ws.sendBIN((uint8_t*)packet.data(), packet.size());
}
void sendPacket(uint8_t headerByte, const std::vector<uint8_t>& body) {
  uint8_t h[5]; h[0] = headerByte;
  size_t n = encodeRemaining(h + 1, body.size());
  std::vector<uint8_t> packet;
  packet.insert(packet.end(), h, h + 1 + n);
  packet.insert(packet.end(), body.begin(), body.end());
  sendMqtt(packet);
}
void mqttConnectPacket() {
  std::vector<uint8_t> b;
  appendMqttString(b, "MQTT");
  b.push_back(4);              // MQTT 3.1.1
  b.push_back(USE_EMQX_RELAY ? 0x02 : 0xC2); // clean session; Shiftr also uses credentials
  b.push_back(0); b.push_back(30);
  appendMqttString(b, "sanket_" + deviceID);
  appendMqttString(b, USE_EMQX_RELAY ? "" : SHIFTR_USER);
  appendMqttString(b, USE_EMQX_RELAY ? "" : SHIFTR_PASS);
  sendPacket(0x10, b);
  Serial.println("[MQTT] CONNECT sent");
}
void mqttSubscribe(const String& t) {
  std::vector<uint8_t> b;
  uint16_t id = mqttPacketId++;
  b.push_back(id >> 8); b.push_back(id & 0xff);
  appendMqttString(b, t); b.push_back(0);
  sendPacket(0x82, b);
}
void mqttPublish(const String& t, const uint8_t* data, size_t len, bool retain=false) {
  std::vector<uint8_t> b;
  appendMqttString(b, t);
  if (len) b.insert(b.end(), data, data + len);
  sendPacket(retain ? 0x31 : 0x30, b);
}
void mqttPublish(const String& t, const String& s, bool retain=false) {
  mqttPublish(t, (const uint8_t*)s.c_str(), s.length(), retain);
}
bool decodeRemaining(const uint8_t* p, size_t len, size_t& value, size_t& used) {
  value = 0; used = 0; size_t mult = 1; uint8_t digit;
  do {
    if (used >= len || used >= 4) return false;
    digit = p[used++]; value += (digit & 127) * mult; mult *= 128;
  } while (digit & 128);
  return true;
}

// ---------------- SETTINGS / PRESENCE ----------------
void loadSettings() {
  prefs.begin("sanketptt", false);
  wifiSSID1 = prefs.getString("ssid1", WIFI_DEFAULT);
  wifiPASS1 = prefs.getString("pass1", "");
  wifiSSID2 = prefs.getString("ssid2", "");
  wifiPASS2 = prefs.getString("pass2", "");
  deviceName = prefs.getString("name", DEVICE_DEFAULT);
  addressee = prefs.getString("to", "ALL");
  configPIN = deviceID.substring(2);
}
void saveSettings() {
  prefs.putString("ssid1", wifiSSID1); prefs.putString("pass1", wifiPASS1);
  prefs.putString("ssid2", wifiSSID2); prefs.putString("pass2", wifiPASS2);
  prefs.putString("name", deviceName); prefs.putString("to", addressee);
}
uint64_t nowMs() { return (uint64_t)time(nullptr) * 1000ULL + (millis() % 1000); }
void syncClock() {
  configTime(0, 0, "pool.ntp.org", "time.google.com");
  for (uint8_t i = 0; i < 20 && time(nullptr) < 1700000000; ++i) delay(500);
  clockReady = time(nullptr) >= 1700000000;
  Serial.println(clockReady ? "[TIME] Clock synchronized" : "[TIME] NTP unavailable");
}
void sendPresence() {
  if (!mqttConnected) return;
  StaticJsonDocument<256> doc;
  doc["id"] = deviceID; doc["name"] = deviceName;
  doc["ts"] = nowMs();
  doc["to"] = addressee;
  char out[256]; size_t n = serializeJson(doc, out, sizeof(out));
  mqttPublish(tPresenceSelf, (const uint8_t*)out, n, true);
}
void sendFloor(const char* type) {
  if (!mqttConnected) return;
  StaticJsonDocument<192> doc;
  doc["t"] = type; doc["id"] = deviceID; doc["name"] = deviceName;
  doc["ts"] = (uint64_t)time(nullptr) * 1000ULL;
  char out[192]; size_t n = serializeJson(doc, out, sizeof(out));
  mqttPublish(tFloor, (const uint8_t*)out, n);
}

// ---------------- WIFI / CONFIG PORTAL ----------------
bool connectWiFi(const String& ssid, const String& pass) {
  if (!ssid.length()) return false;
  Serial.printf("[WIFI] Connecting to %s\n", ssid.c_str());
  WiFi.disconnect(false, false);
  WiFi.begin(ssid.c_str(), pass.c_str());
  uint32_t start = millis();
  while (millis() - start < 15000) {
    if (WiFi.status() == WL_CONNECTED) {
      Serial.printf("[WIFI] Connected: %s\n", WiFi.localIP().toString().c_str());
      return true;
    }
    delay(250);
  }
  Serial.println("[WIFI] Connection timed out");
  return false;
}
void startWebServer() {
  server.on("/", HTTP_GET, []() {
    String html = R"rawliteral(
<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sanket Radio Setup</title><style>
body{font-family:Arial;background:#10243a;color:#fff;padding:20px;max-width:520px;margin:auto}
input{width:100%;padding:12px;margin:8px 0;box-sizing:border-box}
button{width:100%;padding:14px;background:#138808;color:white;border:0;font-size:17px}
</style></head><body><h2>SANKET PTT RADIO SETUP</h2>
<form action="/save" method="POST">
<label>Configuration PIN</label><input name="pin" required>
<h3>Primary Wi-Fi</h3><label>SSID</label><input name="s1" value=")rawliteral" + wifiSSID1 + R"rawliteral(" required>
<label>Password</label><input name="p1" type="password">
<h3>Secondary Wi-Fi</h3><label>SSID</label><input name="s2" value=")rawliteral" + wifiSSID2 + R"rawliteral(">
<label>Password</label><input name="p2" type="password">
<h3>Radio settings</h3><label>Device name</label><input name="name" value=")rawliteral" + deviceName + R"rawliteral(">
<label>Addressee</label><input name="to" value=")rawliteral" + addressee + R"rawliteral(">
<button type="submit">SAVE AND RESTART</button></form></body></html>)rawliteral";
    server.send(200, "text/html", html);
  });
  server.on("/save", HTTP_POST, []() {
    if (server.arg("pin") != configPIN) {
      server.send(403, "text/plain", "Wrong PIN"); return;
    }
    wifiSSID1 = server.arg("s1"); wifiPASS1 = server.arg("p1");
    wifiSSID2 = server.arg("s2"); wifiPASS2 = server.arg("p2");
    deviceName = server.arg("name"); addressee = server.arg("to");
    saveSettings();
    server.send(200, "text/plain", "Saved. Restarting radio.");
    delay(800); ESP.restart();
  });
  server.begin();
  Serial.println("[WEB] Setup page started");
}
void startSetupAP() {
  portalMode = true; WiFi.mode(WIFI_AP);
  String suffix = deviceID.substring(2);
  String ap = "Sanket-Setup-" + suffix;
  String password = "Skt-" + suffix + "!";
  WiFi.softAP(ap.c_str(), password.c_str());
  Serial.println("[SETUP] Connect to AP: " + ap);
  Serial.println("[SETUP] Password: " + password);
  Serial.println("[SETUP] Open http://192.168.4.1");
  Serial.println("[SETUP] Configuration PIN: " + configPIN);
  startWebServer();
}

// ---------------- FLOOR / AUDIO ----------------
void requestPTT() {
  if (!mqttConnected || !joined || !clockReady || pttDown) return;
  if (floorID.length() && floorID != deviceID) {
    Serial.println("[PTT] CHANNEL BUSY"); return;
  }
  pttDown = true; claimPending = true; floorGranted = false;
  claimTime = millis(); sendFloor("claim");
  Serial.println("[PTT] REQUESTING FLOOR");
}
void releasePTT() {
  if (pttDown || claimPending || floorGranted) sendFloor("release");
  pttDown = false; claimPending = false; floorGranted = false;
  if (floorID == deviceID) { floorID = ""; floorName = ""; }
  digitalWrite(STATUS_LED, LOW);
}
void handleFloor(const uint8_t* payload, size_t len) {
  StaticJsonDocument<256> doc;
  if (deserializeJson(doc, payload, len)) return;
  String type = doc["t"] | "", id = doc["id"] | "", name = doc["name"] | "";
  if (!id.length()) return;
  if (type == "release") {
    if (floorID == id) { floorID = ""; floorName = ""; floorTimestamp = 0; }
    if (id == deviceID) { floorGranted = false; claimPending = false; }
    return;
  }
  if (type != "claim" && type != "hb") return;
  if (!floorID.length() || floorID == id) {
    floorID = id; floorName = name;
  } else if (type == "claim") {
    // Match website arbitration: timestamp, then name+id tie-break.
    uint64_t incomingTs = doc["ts"] | 0ULL;
    // Keep the current holder unless this claim wins the deterministic tie-break.
    String incomingKey = name + id, currentKey = floorName + floorID;
    if (incomingTs && incomingKey < currentKey) {
      floorID = id; floorName = name;
    }
  }
  if (pttDown && floorID != deviceID) {
    pttDown = false; floorGranted = false; claimPending = false;
    digitalWrite(STATUS_LED, LOW);
    Serial.println("[PTT] Floor lost to another station");
  }
}
void handleAudio(const uint8_t* payload, size_t len) {
  if (!audioReady || len < 2) return;
  uint8_t idLen = payload[0];
  if (!idLen || idLen > 40 || len <= (size_t)(1 + idLen)) return;
  String sender; sender.reserve(idLen);
  for (uint8_t i=0; i<idLen; ++i) sender += (char)payload[1+i];
  if (sender == deviceID || sender != floorID) return;
  size_t pcmLen = (len - 1 - idLen) & ~((size_t)1);
  if (!pcmLen || pcmLen > AUDIO_BYTES) return;
  RxFrame frame; frame.length = pcmLen;
  memcpy(frame.data, payload + 1 + idLen, pcmLen);
  if (rxQueue) xQueueSend(rxQueue, &frame, 0);
}
void processMqttPacket(const uint8_t* p, size_t len) {
  if (len < 2) return;
  uint8_t type = p[0] >> 4; size_t rem=0, used=0;
  if (!decodeRemaining(p+1, len-1, rem, used)) return;
  size_t off = 1 + used;
  if (off + rem > len) return;
  const uint8_t* b = p + off;
  if (type == 2) {
    if (rem >= 2 && b[1] == 0) {
      mqttConnected = true; joined = true; lastPing = millis();
      Serial.println("[MQTT] Connected over WSS");
      mqttSubscribe(tPresenceWildcard); mqttSubscribe(tFloor); mqttSubscribe(tAudio);
      sendPresence(); lastPresence = millis();
      Serial.println("[RADIO] JOINED VIRTUAL");
    } else {
      mqttConnected = false;
      Serial.printf("[MQTT] CONNACK rejected: %u\n", rem >= 2 ? b[1] : 255);
    }
    return;
  }
  if (type == 3) {
    if (rem < 2) return;
    uint16_t topicLen = ((uint16_t)b[0] << 8) | b[1];
    if (rem < (size_t)(2 + topicLen)) return;
    String t; t.reserve(topicLen);
    for (uint16_t i=0; i<topicLen; ++i) t += (char)b[2+i];
    uint8_t qos = (p[0] >> 1) & 3;
    size_t payloadOff = 2 + topicLen + (qos ? 2 : 0);
    if (payloadOff > rem) return;
    const uint8_t* data = b + payloadOff; size_t n = rem - payloadOff;
    if (t == tFloor) handleFloor(data, n);
    else if (t == tAudio) handleAudio(data, n);
  }
}
void consumeMqtt(const uint8_t* data, size_t len) {
  if (!len) return;
  if (mqttRxLen + len > sizeof(mqttRx)) {
    mqttRxLen = 0; Serial.println("[MQTT] RX buffer overflow"); return;
  }
  memcpy(mqttRx + mqttRxLen, data, len); mqttRxLen += len;
  while (mqttRxLen >= 2) {
    size_t rem=0, used=0;
    if (!decodeRemaining(mqttRx+1, mqttRxLen-1, rem, used)) break;
    size_t total = 1 + used + rem;
    if (total > sizeof(mqttRx)) { mqttRxLen=0; return; }
    if (mqttRxLen < total) break;
    processMqttPacket(mqttRx, total);
    memmove(mqttRx, mqttRx+total, mqttRxLen-total);
    mqttRxLen -= total;
  }
}

// ---------------- WEBSOCKET ----------------
void websocketEvent(WStype_t type, uint8_t* payload, size_t len) {
  switch (type) {
    case WStype_CONNECTED:
      wsConnected = true; mqttConnected = false; joined = false; mqttRxLen = 0;
      Serial.println("[WSS] WebSocket connected"); mqttConnectPacket(); break;
    case WStype_DISCONNECTED:
      wsConnected = false; mqttConnected = false; joined = false;
      floorID = ""; floorName = ""; floorTimestamp = 0; releasePTT();
      mqttRxLen = 0; Serial.println("[WSS] Disconnected; reconnecting"); break;
    case WStype_BIN: consumeMqtt(payload, len); break;
    case WStype_ERROR: Serial.println("[WSS] WebSocket error"); break;
    default: break;
  }
}
void startWSS() {
  ws.onEvent(websocketEvent);
  ws.setReconnectInterval(5000);
  if (USE_EMQX_RELAY) {
    ws.beginSSL("broker.emqx.io", 8084, "/mqtt", "", "mqtt");
    Serial.println("[WSS] Relay EMQX selected; browser must use EMQX");
  } else {
    ws.beginSSL(SHIFTR_HOST, SHIFTR_PORT, SHIFTR_PATH, "", "mqtt");
    Serial.println("[WSS] Relay Shiftr selected; browser must use Shiftr");
  }
}

// ---------------- AUDIO PROCESSING ----------------
void processAudio() {
  if (!audioReady) return;
  RxFrame rx;
  if (rxQueue && xQueueReceive(rxQueue, &rx, 0) == pdTRUE)
    audio.write(rx.data, rx.length);

  if (!pttDown || !floorGranted || !mqttConnected) return;
  static int16_t pcm[AUDIO_SAMPLES];
  size_t received = audio.readBytes((uint8_t*)pcm, AUDIO_BYTES);
  received &= ~((size_t)1);
  if (!received) return;
  uint8_t packet[1 + 40 + AUDIO_BYTES];
  uint8_t idLen = (uint8_t)deviceID.length();
  packet[0] = idLen;
  memcpy(packet + 1, deviceID.c_str(), idLen);
  memcpy(packet + 1 + idLen, pcm, received);
  mqttPublish(tAudio, packet, 1 + idLen + received);
}

// ---------------- SERIAL COMMANDS ----------------
void serialCommands() {
  if (!Serial.available()) return;
  String cmd = Serial.readStringUntil('\n'); cmd.trim();
  if (cmd.startsWith("AT+TO=")) {
    addressee = cmd.substring(6); prefs.putString("to", addressee);
    sendPresence(); Serial.println("[AT] ADDRESSEE UPDATED: " + addressee);
  } else if (cmd.startsWith("AT+NAME=")) {
    deviceName = cmd.substring(8); prefs.putString("name", deviceName);
    sendPresence(); Serial.println("[AT] NAME UPDATED: " + deviceName);
  } else if (cmd == "AT+STATUS") {
    Serial.println("SANKET ESP32 STATUS");
    Serial.println(WiFi.localIP());
    Serial.println(mqttConnected ? "MQTT/WSS ONLINE" : "MQTT/WSS OFFLINE");
    Serial.println("CHANNEL: VIRTUAL");
    Serial.println("DEVICE: " + deviceName);
    Serial.println("FLOOR: " + (floorName.length() ? floorName : "FREE"));
    Serial.println("ADDRESSEE: " + addressee);
  } else if (cmd == "AT+HELP") {
    Serial.println("AT+TO=Dispatch"); Serial.println("AT+NAME=Control01");
    Serial.println("AT+STATUS"); Serial.println("AT+HELP");
  }
}

// ---------------- STARTUP / MAIN LOOP ----------------
void setup() {
  Serial.begin(115200); Serial.setTimeout(30);
  pinMode(PTT_PIN, INPUT); // GPIO34 requires external 10K pull-up
  pinMode(AMP_ENABLE, OUTPUT); pinMode(STATUS_LED, OUTPUT);
  digitalWrite(AMP_ENABLE, HIGH); digitalWrite(STATUS_LED, LOW);

  deviceID = makeDeviceID();
  loadSettings();
  String base = topic("");
  tPresenceSelf = base + "presence/" + deviceID;
  tPresenceWildcard = base + "presence/+";
  tFloor = base + "floor"; tAudio = base + "audio";
  rxQueue = xQueueCreate(RX_QUEUE_DEPTH, sizeof(RxFrame));

  Serial.println(); Serial.println("SANKET PTT ESP32 WSS STARTING");
  Serial.println("DEVICE: " + deviceID); Serial.println("CHANNEL: VIRTUAL");
  Serial.println("CONFIG PIN: " + configPIN);

  auto cfg = audio.defaultConfig(RXTX_MODE);
  cfg.sample_rate = AUDIO_RATE; cfg.bits_per_sample = 16; cfg.channels = 1;
  cfg.input_device = ADC_INPUT_LINE1; cfg.output_device = DAC_OUTPUT_ALL;
  audioReady = audio.begin(cfg);
  if (audioReady) { audio.setVolume(0.85); Serial.println("[AUDIO] ES8388 initialized"); }
  else Serial.println("[AUDIO] Initialization failed — check AudioTools/board driver versions");

  WiFi.mode(WIFI_STA); WiFi.setAutoReconnect(true); WiFi.setSleep(false);
  bool ok = connectWiFi(wifiSSID1, wifiPASS1);
  if (!ok) ok = connectWiFi(wifiSSID2, wifiPASS2);
  if (!ok) { startSetupAP(); return; }

  startWebServer();
  startWSS();
}
void loop() {
  serialCommands();
  server.handleClient();
  if (portalMode) { delay(2); return; }

  ws.loop();
  if (WiFi.status() != WL_CONNECTED) {
    releasePTT();
    Serial.println("[WIFI] Lost Wi-Fi; trying saved networks");
    ws.disconnect();
    if (connectWiFi(wifiSSID1, wifiPASS1) || connectWiFi(wifiSSID2, wifiPASS2)) {
      Serial.println("[WIFI] Restored"); syncClock(); startWSS();
    } else { startSetupAP(); return; }
  }

  if (mqttConnected) {
    if (millis() - lastPing >= 15000) {
      const uint8_t ping[] = {0xC0, 0x00};
      ws.sendBIN((uint8_t*)ping, sizeof(ping)); lastPing = millis();
    }
    if (millis() - lastPresence >= 5000) {
      sendPresence(); lastPresence = millis();
    }
    if (floorGranted && millis() - lastHeartbeat >= 5000) {
      sendFloor("hb"); lastHeartbeat = millis();
    }
  }

  static bool lastButton = HIGH;
  bool button = digitalRead(PTT_PIN);
  if (button != lastButton) {
    delay(25); button = digitalRead(PTT_PIN);
    if (button != lastButton) {
      lastButton = button;
      if (button == LOW) requestPTT(); else releasePTT();
    }
  }

  if (claimPending && pttDown && millis() - claimTime >= 750) {
    if (floorID == deviceID && mqttConnected) {
      floorGranted = true; claimPending = false;
      digitalWrite(STATUS_LED, HIGH); Serial.println("[PTT] FLOOR GRANTED — TRANSMITTING");
    } else {
      claimPending = false; pttDown = false;
      digitalWrite(STATUS_LED, LOW); Serial.println("[PTT] FLOOR BUSY / CLAIM NOT CONFIRMED");
    }
  }

  processAudio();
  if (millis() - lastStatusLog > 15000) {
    lastStatusLog = millis();
    if (!mqttConnected) Serial.println("[STATUS] Waiting for WSS/MQTT connection...");
  }
  delay(1);
}
