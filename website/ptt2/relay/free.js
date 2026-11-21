/** A free visit opens one channel with no email or password form. */
import { RELAY_SANKET, loadRelay, savePublicChannel, saveRelay, saveRoom } from "./config.js";

export function isFreeVisit() {
  return new URLSearchParams(location.search).get("free") === "1";
}

export function freeChannel() {
  return new URLSearchParams(location.search).get("ch") || new URLSearchParams(location.search).get("room") || "";
}

/** Apply ?free=1&ch= before the radio starts. Room codes open the Sanket relay. */
export function prepareFreeRelay() {
  if (!isFreeVisit()) return false;
  const channel = freeChannel();
  if (/^RM-/i.test(channel)) {
    saveRelay(RELAY_SANKET);
    saveRoom(channel);
  } else {
    saveRelay("public");
    if (channel) savePublicChannel(channel);
  }
  return true;
}

export function freeNeedsGuest() {
  return isFreeVisit() && loadRelay() === RELAY_SANKET;
}
