/**
 * Client for the Sanket Transcribe server.
 * TODO: pending the real API contract. The intended call is one POST per transmission.
 * Response shape we will accept: { text, language, segments }.
 */
import { isAllowedServer } from "./config.js";

export async function transcribeRemote(serverUrl, wavBuffer, config) {
  if (!isAllowedServer(serverUrl)) {
    throw new Error("Server URL is not a Sanket Transcribe host");
  }
  const root = String(serverUrl).replace(/\/+$/, "");
  const response = await fetch(root + "/transcribe", {
    method: "POST",
    headers: {
      "Content-Type": "audio/wav",
      "X-Sanket-Language": (config && config.language) || "en",
      "X-Sanket-Translate": config && config.translate ? "1" : "0",
    },
    body: wavBuffer,
  });
  if (!response.ok) throw new Error("Sanket Transcribe returned " + response.status);
  const data = await response.json();
  return {
    text: String(data.text || "").trim(),
    language: String(data.language || (config && config.language) || ""),
    segments: Array.isArray(data.segments) ? data.segments : [],
  };
}
