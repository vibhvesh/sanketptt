/** PTT 2 connects exclusively to the authenticated Sanket Relay. */
export const RELAY_SANKET = "sanket";
export const SANKET_UNREACHABLE = "Sanket Relay is unreachable";
export const SANKET_RELAY_ORIGIN = "https://relay.canberravision.com";
export const SANKET_CHANNEL_PASSWORD = "radio123";
export const ROOM_STORAGE_KEY = "sanket.ptt2.relayRoom";

export function loadRoom() {
  try {
    return String(localStorage.getItem(ROOM_STORAGE_KEY) || "")
      .toUpperCase().replace(/[^A-Z0-9-]/g, "").slice(0, 16);
  } catch (e) {
    return "";
  }
}

export function saveRoom(id) {
  const room = String(id || "").toUpperCase().replace(/[^A-Z0-9-]/g, "").slice(0, 16);
  try {
    if (room) localStorage.setItem(ROOM_STORAGE_KEY, room);
    else localStorage.removeItem(ROOM_STORAGE_KEY);
  } catch (e) {
    /* private mode can refuse storage */
  }
  return room;
}

export function relaySpec(roomId) {
  return {
    id: RELAY_SANKET,
    origin: SANKET_RELAY_ORIGIN,
    roomId: String(roomId || loadRoom()),
    brokers: [],
    username: "",
    password: "",
    exclusive: true,
  };
}

export function formatRelayNet(event, relayId, channel) {
  if (event === "unreachable" || event === "disconnected" ||
      String(event || "").indexOf("unreachable") === 0) {
    return SANKET_UNREACHABLE;
  }
  if (event === SANKET_RELAY_ORIGIN) return "Connected to Sanket Relay";
  if (event === "disconnected") return "Reconnecting to Sanket Relay…";
  return "Sanket Relay · " + (channel || "connecting");
}
