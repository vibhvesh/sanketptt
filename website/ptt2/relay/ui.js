import {
  PUBLIC_CHANNELS,
  RELAY_PUBLIC,
  RELAY_SANKET,
  SANKET_UNREACHABLE,
  formatRelayNet,
  loadAccount,
  loadPublicChannel,
  loadRelay,
  loadRoom,
  relaySpec,
  savePublicChannel,
  saveRelay,
  saveRoom,
} from "./config.js";
import { assignedRooms } from "./sanket-socket.js";

const SIGNED_IN_KEY = "sanket.ptt2.signedIn";

function paint(status, text) {
  status.textContent = text;
  status.classList.toggle("down", text === SANKET_UNREACHABLE);
}

function esc(value) {
  return String(value).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
}

function signedIn() {
  if (loadRelay() === RELAY_SANKET) return true;
  try {
    return localStorage.getItem(SIGNED_IN_KEY) === "1";
  } catch (e) {
    return false;
  }
}

function markSignedIn() {
  try {
    localStorage.setItem(SIGNED_IN_KEY, "1");
  } catch (e) {
    /* ignore */
  }
}

function currentValue() {
  return loadRelay() === RELAY_SANKET ? "sanket:" + loadRoom() : "public:" + loadPublicChannel();
}

export function mountRelay(root, onChoose) {
  root.innerHTML = `
    <h3>AVAILABLE CHANNELS</h3>
    <div id="ptt2ChannelChips" role="listbox" aria-label="Available channels"></div>
    <button type="button" id="ptt2SignIn">Sign in to see your channels</button>
    <p id="ptt2RelayStatus"></p>
  `;
  const chips = root.querySelector("#ptt2ChannelChips");
  const signIn = root.querySelector("#ptt2SignIn");
  const status = root.querySelector("#ptt2RelayStatus");
  let sanketRooms = [];
  let showingSanket = signedIn();

  function choose(value) {
    const mark = value.indexOf(":");
    const kind = value.slice(0, mark);
    const id = value.slice(mark + 1);
    const url = new URL(location.href);
    url.searchParams.delete("relay");
    url.searchParams.delete("room");
    url.searchParams.delete("ch");
    history.replaceState(null, "", url.pathname + url.search + url.hash);
    if (kind === "sanket") {
      saveRelay(RELAY_SANKET);
      saveRoom(id);
      paint(status, "Joining " + id + ".");
      onChoose(relaySpec(RELAY_SANKET));
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
    const rows = showingSanket
      ? sanketRooms.map((item) => ({ value: "sanket:" + item.roomId, name: item.roomName || item.roomId }))
      : PUBLIC_CHANNELS.map((item) => ({ value: "public:" + item.id, name: item.name }));
    chips.innerHTML = rows.map((item) => {
      const on = item.value === active ? " is-on" : "";
      return `<button type="button" class="ptt2-chip${on}" data-value="${esc(item.value)}" aria-pressed="${on ? "true" : "false"}">${esc(item.name)}</button>`;
    }).join("");
    signIn.hidden = showingSanket;
  }

  chips.addEventListener("click", (event) => {
    const button = event.target.closest("[data-value]");
    if (!button) return;
    choose(button.getAttribute("data-value"));
  });

  async function signInNow() {
    signIn.disabled = true;
    paint(status, "Signing in…");
    try {
      sanketRooms = await assignedRooms(loadAccount());
      markSignedIn();
      showingSanket = true;
      render();
      paint(status, sanketRooms.length ? "Your channels" : "No channels are assigned to this sign-in.");
    } catch (e) {
      showingSanket = false;
      render();
      paint(status, SANKET_UNREACHABLE);
    } finally {
      signIn.disabled = false;
    }
  }

  signIn.addEventListener("click", () => {
    signInNow();
  });

  window.ptt2SetRelayRooms = (rooms) => {
    sanketRooms = rooms || [];
    if (sanketRooms.length) {
      markSignedIn();
      showingSanket = true;
    }
    render();
  };

  window.ptt2OnRelayNet = function (event, relayId, channel) {
    const text = formatRelayNet(event, relayId, channel);
    paint(status, text);
    render();
    return text;
  };

  render();
  paint(status, loadRelay() === RELAY_SANKET ? "Joining " + loadRoom() + "." : "Joining " + loadPublicChannel() + ".");
  if (showingSanket) signInNow();
}
