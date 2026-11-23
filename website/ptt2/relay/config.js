/** Which MQTT relay PTT 2 uses. The radio asks this module for the broker list. */

export const RELAY_PUBLIC = "public";
export const RELAY_SANKET = "sanket";
export const STORAGE_KEY = "sanket.ptt2.relay";
export const SANKET_UNREACHABLE = "Sanket is unreachable";
export const PUBLIC_CHANNEL_KEY = "sanket.ptt2.publicChannel";

/** Live public channels already used by the web radios. */
export const PUBLIC_CHANNELS = Object.freeze([
  { id: "virtual", name: "Virtual" },
  { id: "master", name: "Master" },
  { id: "city-control", name: "City Control" },
  { id: "kolkata-control", name: "Kolkata Control" },
  { id: "sanket-website-demo", name: "Website demo" },
  { id: "dev", name: "Development" },
  { id: "boondock", name: "Boondock Echo" },
]);

/** Same public relays the web PTT uses today, in the same order. */
export const PUBLIC_BROKERS = Object.freeze([
  "wss://public:public@public.cloud.shiftr.io",
  "wss://broker.emqx.io:8084/mqtt",
  "wss://broker.hivemq.com:8884/mqtt",
  "wss://test.mosquitto.org:8081",
]);

/** Sanket PTT relay. Socket.io app, separate from the transcribe service. */
export const SANKET_RELAY_ORIGIN = "https://relay.canberravision.com";
export const SANKET_CHANNEL_PASSWORD = "radio123";
export const ROOM_STORAGE_KEY = "sanket.ptt2.relayRoom";

export function loadPublicChannel() {
  let stored = "";
  try {
    stored = localStorage.getItem(PUBLIC_CHANNEL_KEY) || "";
  } catch (e) {
    stored = "";
  }
  const query = new URLSearchParams(location.search).get("ch");
  const id = String(query || stored || "virtual").toLowerCase().replace(/[^a-z0-9-]/g, "").slice(0, 40);
  return id || "virtual";
}

export function savePublicChannel(id) {
  const channel = String(id || "").toLowerCase().replace(/[^a-z0-9-]/g, "").slice(0, 40) || "virtual";
  try {
    localStorage.setItem(PUBLIC_CHANNEL_KEY, channel);
  } catch (e) {
    /* ignore */
  }
  return channel;
}

export function loadRoom() {
  let stored = "";
  try {
    stored = localStorage.getItem(ROOM_STORAGE_KEY) || "";
  } catch (e) {
    stored = "";
  }
  const query = new URLSearchParams(location.search).get("room");
  return String(query || stored || "RM-LOBY").toUpperCase().replace(/[^A-Z0-9-]/g, "").slice(0, 16) || "RM-LOBY";
}

export function saveRoom(id) {
  const room = String(id || "").toUpperCase().replace(/[^A-Z0-9-]/g, "").slice(0, 16);
  try {
    localStorage.setItem(ROOM_STORAGE_KEY, room);
  } catch (e) {
    /* ignore */
  }
  // A room query parameter is only an initial deep-link hint. Once the user
  // chooses a room, remove that stale override so it cannot force the old
  // room back on the next loadRoom() call.
  try {
    const url = new URL(location.href);
    if (url.searchParams.has("room")) {
      url.searchParams.delete("room");
      history.replaceState(history.state, "", url.pathname + url.search + url.hash);
    }
  } catch (e) {
    /* URL/history may be unavailable in embedded contexts; stored room remains authoritative. */
  }
  return room;
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
      origin: SANKET_RELAY_ORIGIN,
      roomId: loadRoom(),
      brokers: [],
      username: "",
      password: "",
      exclusive: true,
    };
  }
  return {
    id: RELAY_PUBLIC,
    brokers: PUBLIC_BROKERS.slice(),
    channel: loadPublicChannel(),
    username: "",
    password: "",
    exclusive: false,
  };
}

export function formatRelayNet(event, relayId, channel) {
  if (cleanRelay(relayId) === RELAY_SANKET && (event === "unreachable" || event === "disconnected" || String(event || "").indexOf("unreachable") === 0)) {
    return SANKET_UNREACHABLE;
  }
  const known = PUBLIC_CHANNELS.find((item) => item.id === channel);
  const label = known ? known.name : (channel || "channel");
  if (cleanRelay(relayId) === RELAY_SANKET && event === SANKET_RELAY_ORIGIN) return "Joined " + label;
  if (event === "disconnected") return "Reconnecting.";
  return "Joined " + label;
}
