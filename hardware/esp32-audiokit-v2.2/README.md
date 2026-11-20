# SanketPTT ESP32 Audio Kit V2.2 — Listen-only prototype

This folder contains a prototype Arduino sketch for the AI-Thinker ESP32 Audio Kit V2.2 / ESP32-A1S / ES8388.

## Behavior
- Connects to Wi-Fi and the SanketPTT `virtual` channel.
- Uses MQTT 3.1.1 over secure WebSocket (WSS).
- Subscribes to presence, floor and audio topics.
- Plays 12 kHz, signed 16-bit mono PCM from the current floor owner.
- Does not use the microphone, claim the floor, or transmit audio.

## Arduino IDE dependencies
Install these libraries:
1. Arduino Audio Tools (Phil Schatzmann)
2. Arduino Audio Driver (Phil Schatzmann)
3. arduinoWebSockets (Links2004)
4. ArduinoJson (Benoit Blanchon)

Select **ESP32 Dev Module** for the classic ESP32 target.

## Configure and upload
1. Open `SanketPTT_AudioKit_V2_2_ListenOnly.ino`.
2. Set `WIFI_SSID` and `WIFI_PASSWORD`.
3. Upload and open Serial Monitor at 115200 baud.
4. Check for Wi-Fi, WSS and MQTT connection messages.
5. Ensure the browser client is connected to the same broker relay.

## Relay note
The sketch defaults to `public.cloud.shiftr.io:443`, path `/mqtt`, using the website's public demo credentials. Set `USE_EMQX_RELAY = true` to use EMQX instead; the browser must use the same relay. Brokers do not share messages.

## Prototype limitations
This sketch has not been compiled or tested on the physical board. AudioTools / Audio Driver API compatibility and the board's ES8388 configuration must be confirmed during compilation and hardware testing. TLS certificate validation is not pinned. Public demo brokers are not private or suitable for sensitive communications.

If compilation fails, capture the complete Arduino IDE error output for debugging.
