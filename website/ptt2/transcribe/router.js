import { loadConfig, isAllowedServer } from "./config.js";
import { serverHealthy } from "./detect.js";
import { transcribeLocal } from "./local.js";
import { transcribeRemote } from "./remote.js";

async function runLocal(wavBuffer, config) {
  const result = await transcribeLocal(wavBuffer, config);
  return {
    text: result.text,
    language: result.language,
    segments: result.segments,
    source: "local",
  };
}

/** The PTT client calls only this. Server when it is configured and reachable, otherwise local. */
export async function transcribeTransmission(wavBuffer) {
  const config = loadConfig();
  const wantsServer = config.mode === "server" || config.mode === "auto";
  if (wantsServer && config.serverUrl && isAllowedServer(config.serverUrl)) {
    const health = await serverHealthy(config.serverUrl);
    if (health.ok) {
      try {
        const remote = await transcribeRemote(config.serverUrl, wavBuffer, config);
        return { ...remote, source: "server" };
      } catch (e) {
        const local = await runLocal(wavBuffer, config);
        const message = e && e.message ? e.message : String(e);
        return { ...local, note: "Sanket Transcribe failed (" + message + "). Local fallback." };
      }
    }
    const local = await runLocal(wavBuffer, config);
    return { ...local, note: health.reason || "Sanket Transcribe did not respond. Local fallback." };
  }
  return runLocal(wavBuffer, config);
}
