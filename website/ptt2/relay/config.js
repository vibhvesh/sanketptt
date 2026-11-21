/** Which MQTT relay PTT 2 uses. The radio asks this module for the broker list. */

export const RELAY_PUBLIC = "public";
export const RELAY_SANKET = "sanket";
export const STORAGE_KEY = "sanket.ptt2.relay";
export const SANKET_UNREACHABLE = "Sanket relay unreachable";

/** Same public relays the web PTT uses today, in the same order. */
export const PUBLIC_BROKERS = Object.freeze([
  "wss://public:public@public.cloud.shiftr.io",
  "wss://broker.emqx.io:8084/mqtt",
  "wss://broker.hivemq.com:8884/mqtt",
  "wss://test.mosquitto.org:8081",
]);

/** Sanket PTT relay. Port and path are the knobs for this socket. */
export const SANKET_RELAY_HOST = "stlu-001.sanketptt.com";
export const SANKET_RELAY_PORT = 443;
export const SANKET_RELAY_PATH = "/mqtt";

/**
 * Demo basic-auth logins published at relay.canberravision.com.
 * The radio connects as the operator account.
 */
export const SANKET_RELAY_USERNAME = "operator@relay.local";
export const SANKET_RELAY_PASSWORD = "Radio123!";

export function sanketBrokerUrl() {
  const port = SANKET_RELAY_PORT ? ":" + SANKET_RELAY_PORT : "";
  const path = SANKET_RELAY_PATH.charAt(0) === "/" ? SANKET_RELAY_PATH : "/" + SANKET_RELAY_PATH;
  return "wss://" + SANKET_RELAY_HOST + port + path;
}

export function cleanRelay(value) {
  return String(value || "").toLowerCase() === RELAY_SANKET ? RELAY_SANKET : RELAY_PUBLIC;
}

/** Saved choice, then ?relay= on this visit. Default is the public relays. */
export function loadRelay() {
  let stored = "";
  try {
    stored = localStorage.getItem(STORAGE_KEY) || "";
  } catch (e) {
    stored = "";
  }
  const query = new URLSearchParams(location.search).get("relay");
  return cleanRelay(query || stored);
}

export function saveRelay(id) {
  const relay = cleanRelay(id);
  try {
    localStorage.setItem(STORAGE_KEY, relay);
  } catch (e) {
    /* private mode can refuse storage */
  }
  return relay;
}

/** Brokers and auth for one choice. Sanket is a single socket: the radio must not rotate away from it. */
export function relaySpec(id) {
  const relay = cleanRelay(id);
  if (relay === RELAY_SANKET) {
    return {
      id: RELAY_SANKET,
      brokers: [sanketBrokerUrl()],
      username: SANKET_RELAY_USERNAME,
      password: SANKET_RELAY_PASSWORD,
      exclusive: true,
    };
  }
  return {
    id: RELAY_PUBLIC,
    brokers: PUBLIC_BROKERS.slice(),
    username: "",
    password: "",
    exclusive: false,
  };
}

export function formatRelayNet(event, relayId, channel) {
  if (cleanRelay(relayId) === RELAY_SANKET && (event === "unreachable" || event === "disconnected")) {
    return SANKET_UNREACHABLE;
  }
  const prefix = globalThis.PTT_PREFIX || "";
  const topic = prefix + (channel || "");
  return "relay: " + event + (topic ? " · topic " + topic : "");
}
