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
import { assignedRooms } from "./sanket-socket.js";
import { getToken, rememberedLogin, signIn, signOut } from "./auth.js";

function paint(status, text) {
  status.textContent = text;
  status.classList.toggle("down", text === SANKET_UNREACHABLE);
}

function esc(value) {
  return String(value).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
}

function currentValue() {
  return loadRelay() === RELAY_SANKET ? "sanket:" + loadRoom() : "public:" + loadPublicChannel();
}

export function mountRelay(root, onChoose) {
  root.innerHTML = `
    <h3>AVAILABLE CHANNELS</h3>
    <div id="ptt2ChannelChips" role="listbox" aria-label="Available channels"></div>
    <form id="ptt2Auth">
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
    <button type="button" id="ptt2SignOut" hidden>Sign out</button>
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
    form.hidden = showingSanket;
    signOutButton.hidden = !showingSanket;
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

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    enter(email.value, password.value, remember.checked);
  });

  toggle.addEventListener("click", () => {
    const hidden = password.type === "password";
    password.type = hidden ? "text" : "password";
    toggle.textContent = hidden ? "Hide" : "Show";
  });

  demo.addEventListener("click", () => {
    email.value = "operator@relay.local";
    password.value = "Radio123!";
    remember.checked = false;
    enter(email.value, password.value, false);
  });

  signOutButton.addEventListener("click", () => {
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
  if (!getToken() && !saved) saveRelay(RELAY_PUBLIC);
  if (saved) {
    email.value = saved.email;
    password.value = saved.password;
    remember.checked = true;
  }
  render();
  paint(status, loadRelay() === RELAY_SANKET ? "Joining " + loadRoom() + "." : "Joining " + loadPublicChannel() + ".");
  if (getToken() || saved) enter(email.value, password.value, remember.checked);
}
