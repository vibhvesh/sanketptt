/**
 * Client for Sanket Transcribe.
 * OpenAPI at /openapi.json documents X-Sanket-Language and X-Sanket-Translate.
 * It does not describe a body. A raw audio/wav POST to /api/transcribe is the call
 * that returns {text, language, segments}. Multipart uploads are rejected by the server decoder.
 */
import { isAllowedServer, SANKET_DEMO_USERNAME, SANKET_DEMO_PASSWORD } from "./config.js";

function basicAuth() {
  return "Basic " + btoa(SANKET_DEMO_USERNAME + ":" + SANKET_DEMO_PASSWORD);
}

export async function transcribeRemote(serverUrl, wavBuffer, config) {
  if (!isAllowedServer(serverUrl)) {
    throw new Error("Server URL is not a Sanket Transcribe host");
  }
  const root = String(serverUrl).replace(/\/+$/, "");
  const response = await fetch(root + "/api/transcribe", {
    method: "POST",
    headers: {
      Authorization: basicAuth(),
      "Content-Type": "audio/wav",
      "X-Sanket-Language": (config && config.language) || "en",
      "X-Sanket-Translate": config && config.translate ? "1" : "0",
    },
    body: wavBuffer,
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
}
