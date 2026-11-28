import {
  PUBLIC_CHANNELS,
  RELAY_PUBLIC,
  RELAY_SANKET,
  SANKET_UNREACHABLE,
  formatRelayNet,
  loadPublicChannel,
  loadRelay,
  loadRoom,
  relaySpec,
  savePublicChannel,
  saveRelay,
  saveRoom,
} from "./config.js";
import { assignedRooms, listFreeRooms } from "./sanket-socket.js";
import { getToken, rememberedLogin, signIn, signOut } from "./auth.js";
import { freeUsesVirtualDemo, isFreeVisit, prepareFreeRelay } from "./free.js";
import { GUEST_EMAIL, GUEST_PASSWORD, ensureGuest } from "../../sanket-radios/guest.js";
import { VIRTUAL_DEMO, ensureVirtualDemo, isVirtualFreeChannel } from "./demo.js";

function paint(status, text) {
  status.textContent = text;
  status.classList.toggle("down", text === SANKET_UNREACHABLE);
}

function esc(value) {
  return String(value).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
}

function currentValue() {
  if (freeUsesVirtualDemo() || (isFreeVisit() && loadRelay() === RELAY_SANKET && loadRoom() === VIRTUAL_DEMO.roomId)) {
    return "public:" + VIRTUAL_DEMO.publicId;
  }
  return loadRelay() === RELAY_SANKET ? "sanket:" + loadRoom() : "public:" + loadPublicChannel();
}

function openFreeAccount() {
  return freeUsesVirtualDemo() || (loadRelay() === RELAY_SANKET && loadRoom() === VIRTUAL_DEMO.roomId)
    ? ensureVirtualDemo()
    : ensureGuest();
}

export function mountRelay(root, onChoose) {
  const freeMode = prepareFreeRelay() || isFreeVisit();
  root.innerHTML = `
    <h3>AVAILABLE CHANNELS</h3>
    <div id="ptt2ChannelChips" role="listbox" aria-label="Available channels"></div>
    ${freeMode ? "" : `<form id="ptt2Auth">
      <label for="ptt2Email">Email</label>
      <input id="ptt2Email" type="email" autocomplete="username" inputmode="email">
      <label for="ptt2Password">Password</label>
      <div class="ptt2-pass">
        <input id="ptt2Password" type="password" autocomplete="current-password">
        <button type="button" id="ptt2PassToggle">Show</button>
      </div>
      <label class="ptt2-remember"><input id="ptt2Remember" type="checkbox"> Remember me</label>
      <button type="submit" id="ptt2SignIn">Sign in</button>
      <button type="button" id="ptt2Demo">Use demo account</button>
      <p id="ptt2AuthError" hidden></p>
    </form>
    <button type="button" id="ptt2SignOut" hidden>Sign out</button>`}
    <p id="ptt2RelayStatus"></p>
  `;
  const chips = root.querySelector("#ptt2ChannelChips");
  const form = root.querySelector("#ptt2Auth");
  const email = root.querySelector("#ptt2Email");
  const password = root.querySelector("#ptt2Password");
  const remember = root.querySelector("#ptt2Remember");
  const toggle = root.querySelector("#ptt2PassToggle");
  const demo = root.querySelector("#ptt2Demo");
  const error = root.querySelector("#ptt2AuthError");
  const signOutButton = root.querySelector("#ptt2SignOut");
  const status = root.querySelector("#ptt2RelayStatus");
  let sanketRooms = [];
  let showingSanket = false;

  function showError(message) {
    if (!error) return;
    error.hidden = !message;
    error.textContent = message || "";
  }

  function choose(value) {
    const mark = value.indexOf(":");
    const kind = value.slice(0, mark);
    const id = value.slice(mark + 1);
    const url = new URL(location.href);
    url.searchParams.delete("relay");
    url.searchParams.delete("room");
    if (freeMode) url.searchParams.set("free", "1");
    else url.searchParams.delete("free");
    url.searchParams.set("ch", id);
    if (!freeMode) url.searchParams.delete("ch");
    history.replaceState(null, "", url.pathname + url.search + url.hash);
    if (freeMode && isVirtualFreeChannel(id)) {
      saveRelay(RELAY_SANKET);
      saveRoom(VIRTUAL_DEMO.roomId);
      url.searchParams.set("ch", VIRTUAL_DEMO.publicId);
      history.replaceState(null, "", url.pathname + url.search + url.hash);
      paint(status, "Joining " + VIRTUAL_DEMO.label + ".");
      ensureVirtualDemo().then(() => onChoose(relaySpec(RELAY_SANKET)), () => paint(status, SANKET_UNREACHABLE));
      render();
      return;
    }
    if (kind === "sanket") {
      saveRelay(RELAY_SANKET);
      saveRoom(id);
      paint(status, "Joining " + id + ".");
      const open = () => onChoose(relaySpec(RELAY_SANKET));
      if (freeMode) ensureGuest().then(open, () => paint(status, SANKET_UNREACHABLE));
      else open();
    } else {
      saveRelay(RELAY_PUBLIC);
      savePublicChannel(id);
      paint(status, "Joining " + id + ".");
      onChoose(relaySpec(RELAY_PUBLIC));
    }
    render();
  }

  function render() {
    const active = currentValue();
    const rows = freeMode
      ? PUBLIC_CHANNELS.map((item) => ({ value: "public:" + item.id, name: item.name }))
        .concat(sanketRooms.filter((item) => String(item.roomId).toUpperCase() !== VIRTUAL_DEMO.roomId).map((item) => ({ value: "sanket:" + item.roomId, name: item.roomName || item.roomId })))
      : showingSanket
        ? sanketRooms.map((item) => ({ value: "sanket:" + item.roomId, name: item.roomName || item.roomId }))
        : PUBLIC_CHANNELS.map((item) => ({ value: "public:" + item.id, name: item.name }));
    chips.innerHTML = rows.map((item) => {
      const on = item.value === active ? " is-on" : "";
      return `<button type="button" class="ptt2-chip${on}" data-value="${esc(item.value)}" aria-pressed="${on ? "true" : "false"}">${esc(item.name)}</button>`;
    }).join("");
    if (form) form.hidden = showingSanket;
    if (signOutButton) signOutButton.hidden = !showingSanket;
  }

  function returnToPublic() {
    sanketRooms = [];
    showingSanket = false;
    saveRelay(RELAY_PUBLIC);
    showError("");
    render();
    paint(status, "Joining " + loadPublicChannel() + ".");
    onChoose(relaySpec(RELAY_PUBLIC));
  }

  async function enter(address, secret, keep) {
    showError("");
    paint(status, "Signing in…");
    try {
      await signIn(address, secret, keep);
      sanketRooms = await assignedRooms();
      showingSanket = true;
      render();
      paint(status, sanketRooms.length ? "Your channels" : "No channels are assigned to this sign-in.");
    } catch (e) {
      showingSanket = false;
      render();
      if (e && e.status === 401) showError("Sign-in failed. Check the email and password.");
      else paint(status, SANKET_UNREACHABLE);
    }
  }

  chips.addEventListener("click", (event) => {
    const button = event.target.closest("[data-value]");
    if (!button) return;
    choose(button.getAttribute("data-value"));
  });

  if (form) form.addEventListener("submit", (event) => {
    event.preventDefault();
    enter(email.value, password.value, remember.checked);
  });

  if (toggle && password) toggle.addEventListener("click", () => {
    const hidden = password.type === "password";
    password.type = hidden ? "text" : "password";
    toggle.textContent = hidden ? "Hide" : "Show";
  });

  if (demo) demo.addEventListener("click", () => {
    email.value = GUEST_EMAIL;
    password.value = GUEST_PASSWORD;
    remember.checked = false;
    enter(email.value, password.value, false);
  });

  if (signOutButton) signOutButton.addEventListener("click", () => {
    signOut();
    password.value = "";
    remember.checked = false;
    returnToPublic();
  });

  window.ptt2SetRelayRooms = (rooms) => {
    sanketRooms = rooms || [];
    showingSanket = true;
    render();
  };

  window.ptt2OnRelayNet = function (event, relayId, channel) {
    const text = formatRelayNet(event, relayId, channel);
    paint(status, text);
    render();
    return text;
  };

  const saved = rememberedLogin();
  if (!freeMode && !getToken() && !saved) saveRelay(RELAY_PUBLIC);
  if (!freeMode && saved && email && password && remember) {
    email.value = saved.email;
    password.value = saved.password;
    remember.checked = true;
  }
  render();
  paint(status, loadRelay() === RELAY_SANKET ? "Joining " + loadRoom() + "." : "Joining " + loadPublicChannel() + ".");
  if (freeMode) {
    openFreeAccount().then(async () => {
      sanketRooms = await listFreeRooms();
      render();
    }).catch(() => {
      paint(status, loadRelay() === RELAY_SANKET ? SANKET_UNREACHABLE : "Joining " + loadPublicChannel() + ".");
    });
  } else if (getToken() || saved) enter(email.value, password.value, remember.checked);
}
