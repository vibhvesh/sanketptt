/** A free visit opens one channel with no email or password form. */
import { RELAY_SANKET, loadRelay, savePublicChannel, saveRelay, saveRoom } from "./config.js";
import { VIRTUAL_DEMO, isVirtualFreeChannel } from "./demo.js";

export function isFreeVisit() {
  return new URLSearchParams(location.search).get("free") === "1";
}

export function freeChannel() {
  return new URLSearchParams(location.search).get("ch") || new URLSearchParams(location.search).get("room") || "";
}

/** Virtual is the named relay room. Other free channels stay on their own path. */
export function freeUsesVirtualDemo() {
  return isFreeVisit() && isVirtualFreeChannel(freeChannel());
}

/** Apply ?free=1&ch= before the radio starts. Room codes open the Sanket relay. */
export function prepareFreeRelay() {
  if (!isFreeVisit()) return false;
  const channel = freeChannel();
  if (isVirtualFreeChannel(channel)) {
    saveRelay(RELAY_SANKET);
    saveRoom(VIRTUAL_DEMO.roomId);
  } else if (/^RM-/i.test(channel)) {
    saveRelay(RELAY_SANKET);
    saveRoom(channel);
  } else {
    saveRelay("public");
    if (channel) savePublicChannel(channel);
  }
  return true;
}

export function freeNeedsGuest() {
  return isFreeVisit() && loadRelay() === RELAY_SANKET && !freeUsesVirtualDemo();
}
