/** Transcription settings for the PTT 2 client. Stored locally, overridable from the URL. */

export const STORAGE_KEY = "sanket.ptt2.transcribe";

/** Sanket Transcribe. HTTPS on sanketptt.com only. */
export const SANKET_TRANSCRIBE_SERVER = "https://stlu-001.sanketptt.com";

/** Demo operator account published for this server. */
export const SANKET_DEMO_USERNAME = "operator@relay.local";
export const SANKET_DEMO_PASSWORD = "Radio123!";

/** Extra internal host, if one is assigned later. Empty means it is not allowed yet. */
export const INTERNAL_TRANSCRIBE_HOST = "";

const DEFAULTS = Object.freeze({
  mode: "auto",
  serverUrl: SANKET_TRANSCRIBE_SERVER,
  language: "en",
  translate: false,
});

function cleanMode(value) {
  return value === "local" || value === "server" || value === "auto" ? value : DEFAULTS.mode;
}

export function isAllowedServer(raw) {
  const text = String(raw || "").trim();
  if (!text) return false;
  let parsed;
  try {
    parsed = new URL(text);
  } catch (e) {
    return false;
  }
  if (parsed.protocol !== "https:") return false;
  const host = parsed.hostname.toLowerCase();
  if (host === "sanketptt.com" || host.endsWith(".sanketptt.com")) return true;
  if (INTERNAL_TRANSCRIBE_HOST && host === INTERNAL_TRANSCRIBE_HOST.toLowerCase()) return true;
  return false;
}

function readStored() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch (e) {
    return {};
  }
}

/** Effective settings: saved values, then any URL overrides for this visit. */
export function loadConfig() {
  const stored = readStored();
  const query = new URLSearchParams(location.search);
  const mode = cleanMode(query.get("mode") || stored.mode);
  const storedUrl = String(stored.serverUrl || "").trim();
  const serverUrl = String(query.has("serverUrl") ? query.get("serverUrl") : (storedUrl || DEFAULTS.serverUrl)).trim();
  const language = String(query.get("language") || stored.language || DEFAULTS.language).slice(0, 12);
  const translateRaw = query.has("translate") ? query.get("translate") : stored.translate;
  const translate = translateRaw === true || translateRaw === "1" || translateRaw === "true";
  return {
    mode,
    serverUrl: isAllowedServer(serverUrl) || serverUrl === "" ? serverUrl : "",
    language: language || DEFAULTS.language,
    translate,
    serverAllowed: serverUrl === "" || isAllowedServer(serverUrl),
    rejectedServer: serverUrl !== "" && !isAllowedServer(serverUrl),
  };
}

export function saveConfig(partial) {
  const next = Object.assign({}, loadConfig(), partial);
  const serverUrl = String(next.serverUrl || "").trim();
  const record = {
    mode: cleanMode(next.mode),
    serverUrl: serverUrl === "" || isAllowedServer(serverUrl) ? serverUrl : "",
    language: String(next.language || DEFAULTS.language).slice(0, 12),
    translate: !!next.translate,
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(record));
  return loadConfig();
}
