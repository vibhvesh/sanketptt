/*
  SanketPTT ESP32 Audio Kit V2.2 — LISTEN ONLY
  Prototype for https://sanketptt.com/?ch=virtual
  Hardware: AI-Thinker ESP32 Audio Kit V2.2 / A1S / ES8388
  Audio: 12 kHz, signed 16-bit, mono PCM
  Transport: MQTT 3.1.1 over secure WebSocket (WSS), subprotocol mqtt

  Listen-only: no microphone, PTT, floor claim or audio publishing.
  Configure Wi-Fi below. Public demo relay; not for sensitive communications.
  TLS certificate validation is not pinned in this prototype.
*/

#include <Arduino.h>
#include <vector>
#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include "AudioTools.h"
#include "AudioLibs/I2SCodecStream.h"

const char* WIFI_SSID = "YOUR_WIFI_NAME";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* DEVICE_NAME = "SanketESP32";

static const char* MQTT_HOST = "public.cloud.shiftr.io";
static const uint16_t MQTT_PORT = 443;
static const char* MQTT_WS_PATH = "/mqtt";
static const char* MQTT_USER = "public";
static const char* MQTT_PASS = "public";
static const bool USE_EMQX_RELAY = false;

static const char* TOPIC_PREFIX = "ptt-radio-66ab9178/";
static const char* CHANNEL = "virtual";
static const uint32_t AUDIO_RATE = 12000;
static const size_t MQTT_RX_MAX = 4096;

String deviceId, topicPresenceWildcard, topicFloor, topicAudio, topicPresenceSelf;
String floorOwnerId, floorOwnerName;

I2SCodecStream speaker(AudioKitEs8388V2);
WebSocketsClient ws;
bool speakerReady = false, wsConnected = false, mqttConnected = false, joined = false;
uint16_t mqttPacketId = 1;
uint32_t lastMqttPing = 0, lastPresence = 0, lastReconnectLog = 0;
uint8_t mqttRx[MQTT_RX_MAX];
size_t mqttRxLen = 0;

size_t encodeRemainingLength(uint8_t* dst, size_t value) {
  size_t n = 0;
  do {
    uint8_t digit = value % 128;
    value /= 128;
    if (value > 0) digit |= 0x80;
    dst[n++] = digit;
  } while (value > 0 && n < 4);
  return n;
}

void appendString(std::vector<uint8_t>& b, const String& s) {
  uint16_t n = (uint16_t)s.length();
  b.push_back((uint8_t)(n >> 8));
  b.push_back((uint8_t)n);
  for (size_t i = 0; i < s.length(); ++i) b.push_back((uint8_t)s[i]);
}

bool sendMqttPacket(const uint8_t* packet, size_t length) {
  return wsConnected && length && ws.sendBIN(packet, length);
}

void sendConnect() {
  std::vector<uint8_t> body;
  appendString(body, "MQTT");
  body.push_back(4); body.push_back(0xC2);
  body.push_back(0); body.push_back(30);
  String clientId = "ptt_" + deviceId + "_" + String((uint32_t)millis() % 1000000);
  appendString(body, clientId);
  appendString(body, MQTT_USER);
  appendString(body, MQTT_PASS);
  uint8_t header[5]; header[0] = 0x10;
  size_t rl = encodeRemainingLength(header + 1, body.size());
  std::vector<uint8_t> packet;
  packet.insert(packet.end(), header, header + 1 + rl);
  packet.insert(packet.end(), body.begin(), body.end());
  sendMqttPacket(packet.data(), packet.size());
  Serial.println("[MQTT] CONNECT sent");
}

void sendSubscribe(const String& topic) {
  std::vector<uint8_t> body;
  uint16_t id = mqttPacketId++;
  body.push_back((uint8_t)(id >> 8)); body.push_back((uint8_t)id);
  appendString(body, topic); body.push_back(0);
  uint8_t header[5]; header[0] = 0x82;
  size_t rl = encodeRemainingLength(header + 1, body.size());
  std::vector<uint8_t> packet;
  packet.insert(packet.end(), header, header + 1 + rl);
  packet.insert(packet.end(), body.begin(), body.end());
  sendMqttPacket(packet.data(), packet.size());
}

void sendPublish(const String& topic, const uint8_t* payload, size_t length, bool retain) {
  std::vector<uint8_t> body;
  appendString(body, topic);
  body.insert(body.end(), payload, payload + length);
  uint8_t header[5]; header[0] = retain ? 0x31 : 0x30;
  size_t rl = encodeRemainingLength(header + 1, body.size());
  std::vector<uint8_t> packet;
  packet.insert(packet.end(), header, header + 1 + rl);
  packet.insert(packet.end(), body.begin(), body.end());
  sendMqttPacket(packet.data(), packet.size());
}

void sendPingReq() {
  const uint8_t p[] = {0xC0, 0x00};
  sendMqttPacket(p, sizeof(p));
}

bool decodeRemainingLength(const uint8_t* p, size_t len, size_t& value, size_t& bytesUsed) {
  value = 0; bytesUsed = 0; size_t multiplier = 1; uint8_t digit;
  do {
    if (bytesUsed >= len || bytesUsed >= 4) return false;
    digit = p[bytesUsed++];
    value += (digit & 127) * multiplier;
    multiplier *= 128;
  } while (digit & 128);
  return true;
}

void onFloorMessage(const uint8_t* payload, size_t length) {
  StaticJsonDocument<256> doc;
  if (deserializeJson(doc, payload, length)) return;
  const char* t = doc["t"] | "";
  const char* id = doc["id"] | "";
  const char* name = doc["name"] | "";
  if (!strcmp(t, "release")) {
    if (floorOwnerId == id) {
      floorOwnerId = ""; floorOwnerName = "";
      Serial.println("[RADIO] Floor released");
    }
  } else if (!strcmp(t, "claim") || !strcmp(t, "hb")) {
    floorOwnerId = id; floorOwnerName = name;
    Serial.printf("[RADIO] Current speaker: %s (%s)\n",
                  floorOwnerName.c_str(), floorOwnerId.c_str());
  }
}

void onAudioMessage(const uint8_t* payload, size_t length) {
  if (!speakerReady || length < 2) return;
  uint8_t idLen = payload[0];
  if (!idLen || idLen > 40 || length <= (size_t)(1 + idLen)) return;
  String sender; sender.reserve(idLen);
  for (uint8_t i = 0; i < idLen; ++i) sender += (char)payload[1 + i];
  if (floorOwnerId.isEmpty() || sender != floorOwnerId || sender == deviceId) return;
  const uint8_t* pcm = payload + 1 + idLen;
  size_t pcmBytes = (length - 1 - idLen) & ~((size_t)1);
  if (pcmBytes >= 2) speaker.write(pcm, pcmBytes);
}

void processMqttPacket(const uint8_t* packet, size_t length) {
  if (length < 2) return;
  uint8_t type = packet[0] >> 4;
  size_t remaining = 0, rlBytes = 0;
  if (!decodeRemainingLength(packet + 1, length - 1, remaining, rlBytes)) return;
  size_t bodyOffset = 1 + rlBytes;
  if (bodyOffset + remaining > length) return;
  const uint8_t* body = packet + bodyOffset;

  if (type == 2) {
    if (remaining >= 2 && body[1] == 0) {
      mqttConnected = true; lastMqttPing = millis();
      Serial.println("[MQTT] Connected to relay");
      sendSubscribe(topicPresenceWildcard);
      sendSubscribe(topicFloor);
      sendSubscribe(topicAudio);
      StaticJsonDocument<160> doc;
      doc["id"] = deviceId; doc["name"] = DEVICE_NAME; doc["ts"] = (uint32_t)millis();
      char json[160]; size_t n = serializeJson(doc, json, sizeof(json));
      sendPublish(topicPresenceSelf, (const uint8_t*)json, n, true);
      lastPresence = millis(); joined = true;
      Serial.println("[RADIO] Joined SanketPTT channel: virtual");
      Serial.println("[RADIO] LISTEN ONLY — microphone and transmit disabled");
    } else {
      mqttConnected = false;
      Serial.printf("[MQTT] Connection refused, return code %u\n",
                    remaining >= 2 ? body[1] : 255);
    }
    return;
  }

  if (type == 3) {
    if (remaining < 2) return;
    uint16_t topicLen = ((uint16_t)body[0] << 8) | body[1];
    if (remaining < (size_t)(2 + topicLen)) return;
    String topic; topic.reserve(topicLen);
    for (uint16_t i = 0; i < topicLen; ++i) topic += (char)body[2 + i];
    size_t qos = (packet[0] >> 1) & 0x03;
    size_t payloadOffset = 2 + topicLen + (qos ? 2 : 0);
    if (payloadOffset > remaining) return;
    const uint8_t* payload = body + payloadOffset;
    size_t payloadLen = remaining - payloadOffset;
    if (topic == topicFloor) onFloorMessage(payload, payloadLen);
    else if (topic == topicAudio) onAudioMessage(payload, payloadLen);
  }
}

void consumeWebSocketBytes(const uint8_t* data, size_t length) {
  if (!length) return;
  if (mqttRxLen + length > MQTT_RX_MAX) {
    mqttRxLen = 0; Serial.println("[MQTT] RX buffer overflow; cleared"); return;
  }
  memcpy(mqttRx + mqttRxLen, data, length); mqttRxLen += length;
  while (mqttRxLen >= 2) {
    size_t remaining = 0, rlBytes = 0;
    if (!decodeRemainingLength(mqttRx + 1, mqttRxLen - 1, remaining, rlBytes)) break;
    size_t total = 1 + rlBytes + remaining;
    if (total > MQTT_RX_MAX) {
      mqttRxLen = 0; Serial.println("[MQTT] Invalid oversized packet"); return;
    }
    if (mqttRxLen < total) break;
    processMqttPacket(mqttRx, total);
    memmove(mqttRx, mqttRx + total, mqttRxLen - total);
    mqttRxLen -= total;
  }
}

void webSocketEvent(WStype_t type, uint8_t* payload, size_t length) {
  switch (type) {
    case WStype_CONNECTED:
      wsConnected = true; mqttConnected = false; joined = false; mqttRxLen = 0;
      Serial.println("[WSS] Secure WebSocket connected"); sendConnect(); break;
    case WStype_DISCONNECTED:
      wsConnected = false; mqttConnected = false; joined = false;
      floorOwnerId = ""; floorOwnerName = ""; mqttRxLen = 0;
      Serial.println("[WSS] Disconnected; library will reconnect"); break;
    case WStype_BIN: consumeWebSocketBytes(payload, length); break;
    case WStype_ERROR: Serial.println("[WSS] Error"); break;
    default: break;
  }
}

void connectWiFi() {
  WiFi.mode(WIFI_STA); WiFi.setSleep(false); WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.printf("[WIFI] Connecting to %s", WIFI_SSID);
  uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 30000) {
    delay(500); Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("[WIFI] Connected, IP: "); Serial.println(WiFi.localIP());
  } else {
    Serial.println("[WIFI] Failed. Restarting in 5 seconds.");
    delay(5000); ESP.restart();
  }
}

void startWebSocket() {
  ws.onEvent(webSocketEvent); ws.setReconnectInterval(5000);
  if (USE_EMQX_RELAY) {
    ws.beginSSL("broker.emqx.io", 8084, "/mqtt", "", "mqtt");
    Serial.println("[WSS] Using EMQX relay. Browser must use EMQX too.");
  } else {
    ws.beginSSL(MQTT_HOST, MQTT_PORT, MQTT_WS_PATH, "", "mqtt");
    Serial.println("[WSS] Using Shiftr public relay.");
  }
}

void setup() {
  Serial.begin(115200); delay(700);
  uint64_t mac = ESP.getEfuseMac();
  char id[16]; snprintf(id, sizeof(id), "%08lx", (uint32_t)(mac & 0xFFFFFFFF));
  deviceId = String(id);
  String base = String(TOPIC_PREFIX) + CHANNEL + "/";
  topicPresenceWildcard = base + "presence/+";
  topicFloor = base + "floor"; topicAudio = base + "audio";
  topicPresenceSelf = base + "presence/" + deviceId;

  Serial.println(); Serial.println("======================================");
  Serial.println(" SANKETPTT ESP32 AUDIO KIT V2.2");
  Serial.println(" LISTEN-ONLY MQTT/WSS CLIENT");
  Serial.println("======================================");
  Serial.printf("Device: %s (%s)\n", DEVICE_NAME, deviceId.c_str());
  Serial.println("Channel: virtual");
  connectWiFi();

  Serial.println("[AUDIO] Initializing ES8388 speaker output...");
  auto cfg = speaker.defaultConfig(TX_MODE);
  cfg.sample_rate = AUDIO_RATE; cfg.channels = 1; cfg.bits_per_sample = 16;
  cfg.buffer_count = 6; cfg.buffer_size = 1024;
  speakerReady = speaker.begin(cfg);
  if (speakerReady) {
    speaker.setVolume(0.75); Serial.println("[AUDIO] ES8388 output ready");
  } else Serial.println("[AUDIO] Initialization failed. Check library version/board.");

  startWebSocket();
  Serial.println("[SYSTEM] Startup complete. Waiting for relay and floor audio.");
}

void loop() {
  ws.loop();
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WIFI] Lost connection; reconnecting...");
    WiFi.reconnect(); delay(100); return;
  }
  if (mqttConnected && millis() - lastMqttPing >= 15000) {
    sendPingReq(); lastMqttPing = millis();
  }
  if (mqttConnected && joined && millis() - lastPresence >= 5000) {
    StaticJsonDocument<160> doc;
    doc["id"] = deviceId; doc["name"] = DEVICE_NAME; doc["ts"] = (uint32_t)millis();
    char json[160]; size_t n = serializeJson(doc, json, sizeof(json));
    sendPublish(topicPresenceSelf, (const uint8_t*)json, n, true);
    lastPresence = millis();
  }
  if (millis() - lastReconnectLog > 10000) {
    lastReconnectLog = millis();
    if (!mqttConnected) Serial.println("[STATUS] Waiting for MQTT CONNACK...");
  }
  delay(2);
}
