import { loadConfig, isAllowedServer } from "./config.js";
import { inspectWav } from "./clip.js";
import { serverHealthy } from "./detect.js";
import { transcribeRemote } from "./remote.js";

let queue = Promise.resolve();

async function transcribeOne(wavBuffer, line) {
  const clip = inspectWav(wavBuffer);
  if (!clip.ok) return { source: "skip", text: "too short", skipped: true, note: clip.reason || "too short" };
  const config = loadConfig();
  if (!config.serverUrl || !isAllowedServer(config.serverUrl)) {
    return { source: "failed", text: "transcription unavailable", failed: true, note: "Sanket Transcribe server is not configured. No local transcription is used." };
  }
  const health = await serverHealthy(config.serverUrl);
  if (!health.ok) {
    return { source: "failed", text: "transcription unavailable", failed: true, note: "Sanket Transcribe server is unavailable. No local fallback is permitted. " + health.reason };
  }
  try {
    const result = await transcribeRemote(config.serverUrl, wavBuffer, {}, line);
    return { ...result, source: "server", note: "Transcribed by Sanket Transcribe. Model selection is managed by the server." };
  } catch (e) {
    return { source: "failed", text: "transcription failed", failed: true, note: "Sanket Transcribe request failed. No local fallback is permitted. " + (e && e.message ? e.message : String(e)) };
  }
}

export function transcribeTransmission(wavBuffer, line) {
  const job = queue.then(() => transcribeOne(wavBuffer, line), () => transcribeOne(wavBuffer, line));
  queue = job.then(() => {}, () => {});
  return job;
}
