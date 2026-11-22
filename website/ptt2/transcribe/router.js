import { loadConfig, isAllowedServer } from "./config.js";
import { inspectWav } from "./clip.js";
import { serverHealthy } from "./detect.js";
import { transcribeLocal, translateLocal } from "./local.js";
import { transcribeRemote } from "./remote.js";

const LOCAL_TIMEOUT_MS = 45000;
let queue = Promise.resolve();

function withTimeout(work, ms, label) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(label + " timed out")), ms);
    work.then((value) => { clearTimeout(timer); resolve(value); }, (error) => { clearTimeout(timer); reject(error); });
  });
}

async function runLocal(wavBuffer, config) {
  const result = await withTimeout(transcribeLocal(wavBuffer, config), LOCAL_TIMEOUT_MS, "Local transcription");
  let text = result.text;
  let note = "";
  if (config.translate && config.targetLanguage && config.targetLanguage !== "en") {
    try {
      text = await withTimeout(translateLocal(text, result.language || config.language, config.targetLanguage), LOCAL_TIMEOUT_MS, "Local translation");
    } catch (e) {
      note = "Local translation unavailable: " + (e && e.message ? e.message : String(e));
    }
  }
  return { text, language: result.language, segments: result.segments, source: "local", translated: !note && !!config.translate, targetLanguage: config.targetLanguage, note };
}

async function transcribeOne(wavBuffer, line) {
  const clip = inspectWav(wavBuffer);
  if (!clip.ok) return { source: "skip", text: "too short", skipped: true, note: clip.reason || "too short" };
  const config = loadConfig();
  const wantsServer = config.mode === "server" || config.mode === "auto";
  if (wantsServer && config.serverUrl && isAllowedServer(config.serverUrl)) {
    const health = await serverHealthy(config.serverUrl);
    if (health.ok) {
      try {
        const remote = await transcribeRemote(config.serverUrl, wavBuffer, config, line);
        const unsupported = config.translate && config.targetLanguage && config.targetLanguage !== "en";
        return { ...remote, source: "server", note: unsupported ? "Destination language not applied. Server does not expose a destination-language option; using server default." : "" };
      } catch (e) {
        try {
          const local = await runLocal(wavBuffer, config);
          return { ...local, note: [local.note, "Sanket Transcribe failed (" + (e && e.message ? e.message : String(e)) + "). Local fallback."].filter(Boolean).join(" ") };
        } catch (localError) {
          return { source: "failed", text: "transcription failed", failed: true, note: localError && localError.message ? localError.message : "transcription failed" };
        }
      }
    }
    try {
      const local = await runLocal(wavBuffer, config);
      return { ...local, note: [local.note, health.reason || "Sanket Transcribe did not respond. Local fallback."].filter(Boolean).join(" ") };
    } catch (localError) {
      return { source: "failed", text: "transcription failed", failed: true, note: localError && localError.message ? localError.message : "Local transcription failed" };
    }
  }
  try { return await runLocal(wavBuffer, config); }
  catch (e) { return { source: "failed", text: "transcription failed", failed: true, note: e && e.message ? e.message : "" }; }
}

export function transcribeTransmission(wavBuffer, line) {
  const job = queue.then(() => transcribeOne(wavBuffer, line), () => transcribeOne(wavBuffer, line));
  queue = job.then(() => {}, () => {});
  return job;
}
