import { isAllowedServer } from "./config.js";

/** Placeholder health check for the Sanket Transcribe server. */
export async function serverHealthy(serverUrl) {
  if (!isAllowedServer(serverUrl)) return false;
  const root = String(serverUrl).replace(/\/+$/, "");
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 4000);
  try {
    const response = await fetch(root + "/health", { method: "GET", signal: controller.signal, cache: "no-store" });
    return response.ok;
  } catch (e) {
    return false;
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
