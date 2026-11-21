import { loadConfig, isAllowedServer } from "./config.js";
import { inspectWav } from "./clip.js";
import { serverHealthy } from "./detect.js";
import { transcribeLocal } from "./local.js";
import { transcribeRemote } from "./remote.js";

const LOCAL_TIMEOUT_MS = 45000;
let queue = Promise.resolve();

function withTimeout(work, ms, label) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(label + " timed out")), ms);
    work.then((value) => {
      clearTimeout(timer);
      resolve(value);
    }, (error) => {
      clearTimeout(timer);
      reject(error);
    });
  });
}

async function runLocal(wavBuffer, config) {
  const result = await withTimeout(transcribeLocal(wavBuffer, config), LOCAL_TIMEOUT_MS, "Local transcription");
  return {
    text: result.text,
    language: result.language,
    segments: result.segments,
    source: "local",
  };
}

async function transcribeOne(wavBuffer) {
  const clip = inspectWav(wavBuffer);
  if (!clip.ok) {
    return { source: "skip", text: "too short", skipped: true, note: clip.reason || "too short" };
  }
  const config = loadConfig();
  const wantsServer = config.mode === "server" || config.mode === "auto";
  if (wantsServer && config.serverUrl && isAllowedServer(config.serverUrl)) {
    const health = await serverHealthy(config.serverUrl);
    if (health.ok) {
      try {
        const remote = await transcribeRemote(config.serverUrl, wavBuffer, config);
        return { ...remote, source: "server" };
      } catch (e) {
        try {
          const local = await runLocal(wavBuffer, config);
          const message = e && e.message ? e.message : String(e);
          return { ...local, note: "Sanket Transcribe failed (" + message + "). Local fallback." };
        } catch (localError) {
          return { source: "failed", text: "transcription failed", failed: true, note: localError && localError.message ? localError.message : "transcription failed" };
        }
      }
    }
    try {
      const local = await runLocal(wavBuffer, config);
      return { ...local, note: health.reason || "Sanket Transcribe did not respond. Local fallback." };
    } catch (localError) {
      return { source: "failed", text: "transcription failed", failed: true };
    }
  }
  try {
    return await runLocal(wavBuffer, config);
  } catch (e) {
    return { source: "failed", text: "transcription failed", failed: true, note: e && e.message ? e.message : "" };
  }
}

/** One clip at a time, so two rows cannot take each other's result. */
export function transcribeTransmission(wavBuffer) {
  const job = queue.then(() => transcribeOne(wavBuffer), () => transcribeOne(wavBuffer));
  queue = job.then(() => {}, () => {});
  return job;
}
