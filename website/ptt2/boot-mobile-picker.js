import { mountSettings, watchRecorder } from "./transcribe/ui.js";
import { RELAY_SANKET, loadRelay, relaySpec } from "./relay/config.js";
import { freeNeedsGuest, prepareFreeRelay } from "./relay/free.js";
import { mountRelay } from "./relay/ui-mobile-picker.js";
import { openSanketRelay } from "./relay/sanket-socket.js";
import { ensureGuest } from "../sanket-radios/guest.js";

window.ptt2OpenSanket = openSanketRelay;
prepareFreeRelay();

const channels = document.getElementById("ptt2ChannelBar");
if (channels) {
  mountRelay(channels, (spec) => {
    if (typeof window.ptt2UseRelay === "function") window.ptt2UseRelay(spec);
  }, () => {
    if (typeof window.ptt2StopRadio === "function") window.ptt2StopRadio();
  });
}
const settings = document.getElementById("ptt2Settings");
if (settings) mountSettings(settings);
const settingsToggle = document.getElementById("ptt2SettingsToggle");
if (settings && settingsToggle) {
  settingsToggle.addEventListener("click", () => {
    settings.hidden = !settings.hidden;
    settingsToggle.setAttribute("aria-expanded", String(!settings.hidden));
    if (!settings.hidden) settings.scrollIntoView({ behavior: "smooth", block: "nearest" });
  });
}
const powerOff = document.getElementById("ptt2PowerOff");
if (powerOff) {
  powerOff.addEventListener("click", () => {
    if (typeof window.ptt2StopRadio === "function") window.ptt2StopRadio();
    location.reload();
  });
}

const power = document.getElementById("go");
const talk = document.getElementById("ptt");
if (power && talk && channels) {
  power.addEventListener("click", () => talk.before(channels));
}
if (typeof rec !== "undefined" && typeof renderLog === "function") {
  watchRecorder(rec, renderLog);
}
async function openInitialRelay() {
  if (freeNeedsGuest() && loadRelay() === RELAY_SANKET) {
    try {
      await ensureGuest();
    } catch (e) {
      /* The channel bar reports that the free room could not be opened. */
    }
  }
  if (typeof window.ptt2UseRelay === "function") window.ptt2UseRelay(relaySpec(loadRelay()));
}
openInitialRelay();
