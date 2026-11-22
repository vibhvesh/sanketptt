/** PTT transcription is always handled by the central Sanket Transcribe service. */
export const STORAGE_KEY = "sanket.ptt2.transcribe";
export const SANKET_TRANSCRIBE_SERVER = "https://stlu-001.sanketptt.com";
export const INTERNAL_TRANSCRIBE_HOST = "";
export const SERVER_SANKET = "sanket";
export const SERVER_CUSTOM = "custom";

export function isPresetServer(raw) {
  return String(raw || "").trim().replace(/\/+$/, "") === SANKET_TRANSCRIBE_SERVER;
}

export function isAllowedServer(raw) {
  try {
    const parsed = new URL(String(raw || "").trim());
    return parsed.protocol === "https:" && !!parsed.hostname;
  } catch (e) {
    return false;
  }
}

export function loadConfig() {
  return {
    mode: "server",
    serverChoice: SERVER_SANKET,
    serverUrl: SANKET_TRANSCRIBE_SERVER,
    language: "auto",
    translate: false,
    targetLanguage: "",
    serverAllowed: true,
    rejectedServer: false,
  };
}

export function saveConfig() {
  return loadConfig();
}
