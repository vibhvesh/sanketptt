import { mountSettings, watchRecorder } from "./transcribe/ui.js";
import { mountRelay } from "./relay/ui.js";
import { openSanketRelay } from "./relay/sanket-socket.js";

window.ptt2OpenSanket = openSanketRelay;

const channels = document.getElementById("ptt2ChannelBar");
if (channels) {
  mountRelay(channels, (spec) => {
    if (typeof window.ptt2UseRelay === "function") window.ptt2UseRelay(spec);
  });
}
const settings = document.getElementById("ptt2Settings");
if (settings) mountSettings(settings);
const power = document.getElementById("go");
const talk = document.getElementById("ptt");
if (power && talk && channels) {
  power.addEventListener("click", () => talk.before(channels));
}
if (typeof rec !== "undefined" && typeof renderLog === "function") {
  watchRecorder(rec, renderLog);
}
