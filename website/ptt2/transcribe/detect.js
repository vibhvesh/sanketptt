import { isAllowedServer } from "./config.js";

/** Health check. A thrown fetch from the browser is how a CORS block shows up. */
export async function serverHealthy(serverUrl) {
  if (!isAllowedServer(serverUrl)) return { ok: false, reason: "Server URL is not a Sanket Transcribe host." };
  const root = String(serverUrl).replace(/\/+$/, "");
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 4000);
  try {
    const response = await fetch(root + "/health", { method: "GET", signal: controller.signal, cache: "no-store" });
    if (!response.ok) return { ok: false, reason: "Sanket Transcribe returned " + response.status + "." };
    return { ok: true, reason: "" };
  } catch (e) {
    const message = e && e.message ? e.message : String(e);
    const blocked = /cors|access-control/i.test(message);
    return {
      ok: false,
      reason: blocked
        ? "Browser blocked Sanket Transcribe (" + message + "). No local fallback is configured."
        : "Sanket Transcribe did not respond (" + message + "). No local fallback is configured.",
    };
  } finally {
    clearTimeout(timer);
  }
}

/** This browser can run the local Whisper model when WebAssembly is present. */
export function localCapability() {
  const wasm = typeof WebAssembly === "object" && typeof WebAssembly.instantiate === "function";
  let webgpu = false;
  try {
    webgpu = typeof navigator !== "undefined" && !!navigator.gpu;
  } catch (e) {
    webgpu = false;
  }
  return { wasm, webgpu, ok: wasm };
}
