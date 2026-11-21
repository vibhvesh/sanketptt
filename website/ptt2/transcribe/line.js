/** Which Sanket line a clip belongs to. Public channels have no line. */

export const LINE_RELAY_HOST = "relay.canberravision.com";

const ISO = {
  en: "en",
  english: "en",
  hi: "hi",
  hindi: "hi",
  gu: "gu",
  gujarati: "gu",
};

/** ISO 639-1 when the user picked a language. "auto" means leave the line's language alone. */
export function languageHeader(language) {
  const key = String(language || "").trim().toLowerCase();
  if (!key || key === "auto" || key === "line") return "";
  return ISO[key] || "";
}

export function lineFromRadio(radio, entry) {
  if (!radio || radio.relayId !== "sanket") return null;
  const mine = !!(entry && entry.mine);
  return {
    relayHost: radio.relayHost || LINE_RELAY_HOST,
    roomId: radio.ch || "",
    roomName: radio.roomName || "",
    speakerName: (entry && entry.name) || radio.name || radio.username || "",
    speakerId: mine ? (radio.speakerEmail || radio.id || "") : ((entry && entry.id) || ""),
  };
}

/** Query names match the upload schema. The raw transcribe call has no line fields of its own. */
export function lineSearch(line) {
  const params = new URLSearchParams();
  if (!line) return params;
  if (line.relayHost) params.set("relay_external_id", line.relayHost);
  if (line.roomId) params.set("channel_external_id", line.roomId);
  if (line.roomName) params.set("channel_name", line.roomName);
  if (line.speakerName) params.set("speaker_name", line.speakerName);
  if (line.speakerId) params.set("speaker_user_id", line.speakerId);
  return params;
}
