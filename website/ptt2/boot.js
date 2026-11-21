import { mountSettings, watchRecorder } from "./transcribe/ui.js";
import { loadRelay, relaySpec } from "./relay/config.js";
import { mountRelay } from "./relay/ui.js";
import { openSanketRelay } from "./relay/sanket-socket.js";

window.ptt2OpenSanket = openSanketRelay;

const settings = document.getElementById("ptt2Settings");
if (settings) {
  settings.innerHTML = '<div id="ptt2RelayMount"></div><div id="ptt2TranscribeMount"></div>';
  mountRelay(document.getElementById("ptt2RelayMount"), (spec) => {
    if (typeof window.ptt2UseRelay === "function") window.ptt2UseRelay(spec);
  });
  mountSettings(document.getElementById("ptt2TranscribeMount"));
}
if (typeof rec !== "undefined" && typeof renderLog === "function") {
  watchRecorder(rec, renderLog);
}
if (typeof window.ptt2UseRelay === "function") window.ptt2UseRelay(relaySpec(loadRelay()));
