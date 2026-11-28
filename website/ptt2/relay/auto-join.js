/** Free Virtual joins itself: a guest call sign, then Power on, with no dialog. */
import { freeUsesVirtualDemo } from "./free.js";

const NAME_KEY = "sanket.ptt2.freeGuest";

export function freeGuestName() {
  try {
    const saved = sessionStorage.getItem(NAME_KEY);
    if (saved) return saved;
  } catch (e) {
    /* private mode */
  }
  const name = "Guest-" + Math.floor(1000 + Math.random() * 9000);
  try { sessionStorage.setItem(NAME_KEY, name); } catch (e) { /* ignore */ }
  return name;
}

export function armFreeVirtualJoin() {
  if (!freeUsesVirtualDemo()) return;
  document.documentElement.classList.add("ptt-free-virtual");
  const name = document.getElementById("nm");
  const net = document.getElementById("net");
  if (name && !name.value) name.value = freeGuestName();
  if (net) net.textContent = "Connecting…";
  let delay = 500;
  const attempt = () => {
    if (window.ptt2FreeJoined) return;
    if (name && !name.value) name.value = freeGuestName();
    const joined = typeof window.ptt2TryPowerOn === "function" && window.ptt2TryPowerOn();
    if (joined) return;
    if (net) net.textContent = "Connecting…";
    delay = Math.min(Math.round(delay * 1.7), 8000);
    setTimeout(attempt, delay);
  };
  setTimeout(attempt, 400);
}
