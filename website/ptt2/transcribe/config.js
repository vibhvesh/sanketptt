/** Transcription settings for the PTT 2 client. Stored locally, overridable from the URL. */

export const STORAGE_KEY = "sanket.ptt2.transcribe";

/** Sanket Transcribe. HTTPS on sanketptt.com only. */
export const SANKET_TRANSCRIBE_SERVER = "https://stlu-001.sanketptt.com";

/** Extra internal host, if one is assigned later. Empty means it is not allowed yet. */
export const INTERNAL_TRANSCRIBE_HOST = "";

const DEFAULTS = Object.freeze({
  mode: "auto",
  serverUrl: SANKET_TRANSCRIBE_SERVER,
  language: "auto",
  translate: false,
});

function cleanMode(value) {
  return value === "local" || value === "server" || value === "auto" ? value : DEFAULTS.mode;
}

export const SERVER_SANKET = "sanket";
export const SERVER_CUSTOM = "custom";

export function isPresetServer(raw) {
  return String(raw || "").trim().replace(/\/+$/, "") === SANKET_TRANSCRIBE_SERVER;
}

/** A usable transcribe server is any https URL. */
export function isAllowedServer(raw) {
  const text = String(raw || "").trim();
  if (!text) return false;
  let parsed;
  try {
    parsed = new URL(text);
  } catch (e) {
    return false;
  }
  return parsed.protocol === "https:" && !!parsed.hostname;
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
  const fromQuery = query.has("serverUrl");
  const rawUrl = String(fromQuery ? query.get("serverUrl") : storedUrl).trim();
  let serverChoice = stored.serverChoice === SERVER_CUSTOM ? SERVER_CUSTOM : stored.serverChoice === SERVER_SANKET ? SERVER_SANKET : "";
  if (fromQuery || !serverChoice) serverChoice = !rawUrl || isPresetServer(rawUrl) ? SERVER_SANKET : SERVER_CUSTOM;
  const serverUrl = serverChoice === SERVER_SANKET ? SANKET_TRANSCRIBE_SERVER : (isAllowedServer(rawUrl) ? rawUrl : "");
  const language = String(query.get("language") || stored.language || DEFAULTS.language).slice(0, 12);
  const translateRaw = query.has("translate") ? query.get("translate") : stored.translate;
  const translate = translateRaw === true || translateRaw === "1" || translateRaw === "true";
  return {
    mode,
    serverChoice,
    serverUrl,
    language: language || DEFAULTS.language,
    translate,
    serverAllowed: serverChoice === SERVER_SANKET || isAllowedServer(serverUrl),
    rejectedServer: serverChoice === SERVER_CUSTOM && rawUrl !== "" && !isAllowedServer(rawUrl),
  };
}

export function saveConfig(partial) {
  const next = Object.assign({}, loadConfig(), partial);
  const serverChoice = next.serverChoice === SERVER_CUSTOM ? SERVER_CUSTOM : SERVER_SANKET;
  const typed = String(next.serverUrl || "").trim();
  const serverUrl = serverChoice === SERVER_SANKET ? SANKET_TRANSCRIBE_SERVER : (isAllowedServer(typed) ? typed : "");
  const record = {
    mode: cleanMode(next.mode),
    serverChoice,
    serverUrl,
    language: String(next.language || DEFAULTS.language).slice(0, 12),
    translate: !!next.translate,
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(record));
  return loadConfig();
}
