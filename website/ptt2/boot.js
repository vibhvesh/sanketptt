import { mountSettings, watchRecorder } from "./transcribe/ui.js";
import { RELAY_SANKET, loadRelay, relaySpec } from "./relay/config.js";
import { freeNeedsGuest, freeUsesVirtualDemo, prepareFreeRelay } from "./relay/free.js";
import { mountRelay } from "./relay/ui.js";
import { openSanketRelay } from "./relay/sanket-socket.js";
import { ensureGuest } from "../sanket-radios/guest.js";
import { ensureVirtualDemo } from "./relay/demo.js";

window.ptt2OpenSanket = openSanketRelay;
prepareFreeRelay();

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
async function openInitialRelay() {
  try {
    if (freeUsesVirtualDemo()) await ensureVirtualDemo();
    else if (freeNeedsGuest() && loadRelay() === RELAY_SANKET) await ensureGuest();
  } catch (e) {
    /* The channel bar reports that the free room could not be opened. */
  }
  if (typeof window.ptt2UseRelay === "function") window.ptt2UseRelay(relaySpec(loadRelay()));
}
openInitialRelay();
