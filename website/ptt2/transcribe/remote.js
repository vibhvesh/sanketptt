/**
 * Client for Sanket Transcribe.
 * The radio sends 16-bit mono PCM WAV at 12 kHz (Content-Type: audio/wav), not WebM/Opus.
 * OpenAPI documents X-Sanket-Language and X-Sanket-Translate. A raw WAV body is the call that works.
 * Each attempt aborts after 15s. One retry, then the caller decides.
 */
import { isAllowedServer, SANKET_DEMO_USERNAME, SANKET_DEMO_PASSWORD } from "./config.js";

export const REQUEST_TIMEOUT_MS = 15000;
const ATTEMPTS = 2;

function basicAuth() {
  return "Basic " + btoa(SANKET_DEMO_USERNAME + ":" + SANKET_DEMO_PASSWORD);
}

async function postOnce(serverUrl, wavBuffer, config) {
  const root = String(serverUrl).replace(/\/+$/, "");
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(root + "/api/transcribe", {
      method: "POST",
      headers: {
        Authorization: basicAuth(),
        "Content-Type": "audio/wav",
        "X-Sanket-Language": (config && config.language) || "en",
        "X-Sanket-Translate": config && config.translate ? "1" : "0",
      },
      body: wavBuffer,
      signal: controller.signal,
    });
    if (!response.ok) throw new Error("Sanket Transcribe returned " + response.status);
    const data = await response.json();
    const segments = Array.isArray(data.segments) ? data.segments.map((segment) => ({
      text: String(segment && segment.text || "").trim(),
      start: segment && segment.start != null ? segment.start : null,
      end: segment && segment.end != null ? segment.end : null,
    })) : [];
    return {
      text: String(data.text || "").trim(),
      language: String(data.language || (config && config.language) || ""),
      segments,
    };
  } catch (e) {
    if (e && e.name === "AbortError") throw new Error("timed out");
    throw e;
  } finally {
    clearTimeout(timer);
  }
}

export async function transcribeRemote(serverUrl, wavBuffer, config) {
  if (!isAllowedServer(serverUrl)) {
    throw new Error("Server URL is not a Sanket Transcribe host");
  }
  let lastError = new Error("Sanket Transcribe failed");
  for (let attempt = 0; attempt < ATTEMPTS; attempt++) {
    try {
      return await postOnce(serverUrl, wavBuffer, config);
    } catch (e) {
      lastError = e instanceof Error ? e : new Error(String(e));
    }
  }
  throw lastError;
}
