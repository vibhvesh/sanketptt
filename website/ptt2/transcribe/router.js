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
    const up = await serverHealthy(config.serverUrl);
    if (up) {
      try {
        const remote = await transcribeRemote(config.serverUrl, wavBuffer, config);
        return { ...remote, source: "server" };
      } catch (e) {
        const local = await runLocal(wavBuffer, config);
        return local;
      }
    }
  }
  return runLocal(wavBuffer, config);
}
