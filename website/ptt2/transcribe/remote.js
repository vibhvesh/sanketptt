/**
 * Client for Sanket Transcribe.
 * The radio sends 16-bit mono PCM WAV at 12 kHz (Content-Type: audio/wav), not WebM/Opus.
 * OpenAPI on this call only documents X-Sanket-Language and X-Sanket-Translate.
 * Line identity is sent as the upload field names on the query string, because extra
 * X-Sanket-* headers are not in the CORS allow list and /api/uploads requires a cockpit login.
 * Each attempt aborts after 15s. One retry, then the caller decides.
 */
import { isAllowedServer } from "./config.js";
import { basicAuthHeader } from "../relay/auth.js";
import { lineSearch } from "./line.js";

export const REQUEST_TIMEOUT_MS = 15000;
const ATTEMPTS = 2;

async function postOnce(serverUrl, wavBuffer, config, line) {
  const root = String(serverUrl).replace(/\/+$/, "");
  const target = new URL(root + "/api/transcribe");
  const identity = lineSearch(line);
  identity.forEach((value, key) => target.searchParams.set(key, value));
  const headers = { "Content-Type": "audio/wav" };
  const auth = basicAuthHeader();
  if (auth) headers.Authorization = auth;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(target, {
      method: "POST",
      headers,
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

export async function transcribeRemote(serverUrl, wavBuffer, config, line) {
  if (!isAllowedServer(serverUrl)) {
    throw new Error("Server URL is not a Sanket Transcribe host");
  }
  let lastError = new Error("Sanket Transcribe failed");
  for (let attempt = 0; attempt < ATTEMPTS; attempt++) {
    try {
      return await postOnce(serverUrl, wavBuffer, config, line);
    } catch (e) {
      lastError = e instanceof Error ? e : new Error(String(e));
    }
  }
  throw lastError;
}
