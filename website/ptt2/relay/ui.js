import {
  PUBLIC_CHANNELS, RELAY_PUBLIC, RELAY_SANKET, SANKET_UNREACHABLE,
  loadPublicChannel, loadRelay, loadRoom, relaySpec, savePublicChannel, saveRelay, saveRoom,
} from "./config.js";
import { assignedRooms } from "./sanket-socket.js";
import { getToken, rememberedLogin, signIn } from "./auth.js";

function esc(value) {
  return String(value).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
}
function paint(status, value) {
  if (!status) return;
  status.textContent = value || "";
  status.classList.toggle("down", value === SANKET_UNREACHABLE);
}
function currentValue() {
  return loadRelay() === RELAY_SANKET ? "sanket:" + loadRoom() : "public:" + loadPublicChannel();
}

export function mountRelay(root, onChoose) {
  const freeMode = new URLSearchParams(location.search).get("free") === "1";
  root.innerHTML = `
    <div class="ptt2-frequency-row">
      <span class="ptt2-frequency-label">FREQUENCY</span>
      <select id="ptt2Frequency" aria-label="Connected frequency"></select>
    </div>
    <form id="ptt2Auth" autocomplete="on">
      <input id="ptt2Email" type="email" aria-label="Email" placeholder="Email" autocomplete="username" required>
      <input id="ptt2Password" type="password" aria-label="Password" placeholder="Password" autocomplete="current-password" required>
      <button type="submit" id="ptt2SignIn">Connect</button>
      <p id="ptt2AuthError" hidden></p>
    </form>
  `;
  const select = root.querySelector("#ptt2Frequency");
  const form = root.querySelector("#ptt2Auth");
  const email = root.querySelector("#ptt2Email");
  const password = root.querySelector("#ptt2Password");
  const error = root.querySelector("#ptt2AuthError");
  let rooms = [];
  let signedIn = false;

  function options() {
    const items = signedIn
      ? rooms.map((r) => ({ value: "sanket:" + r.roomId, name: r.roomName || r.roomId }))
      : [{ value: "sanket:" + loadRoom(), name: loadRoom() }];
    const selected = currentValue();
    select.innerHTML = items.map((item) =>
      '<option value="' + esc(item.value) + '"' + (item.value === selected || (!signedIn && item.value === "sanket:" + loadRoom()) ? " selected" : "") + ">" + esc(item.name) + "</option>"
    ).join("");
    select.hidden = false;
    select.disabled = !signedIn;
  }

  function choose(value) {
    const [kind, id] = String(value).split(":");
    if (kind === "sanket") {
      saveRelay(RELAY_SANKET);
      saveRoom(id);
      onChoose(relaySpec(RELAY_SANKET));
    } else {
      saveRelay(RELAY_PUBLIC);
      savePublicChannel(id);
      onChoose(relaySpec(RELAY_PUBLIC));
    }
  }

  async function connect(address, secret) {
    error.hidden = true;
    try {
      await signIn(address, secret, true);
      rooms = await assignedRooms();
      signedIn = true;
      if (!rooms.some((r) => r.roomId === loadRoom()) && rooms[0]) saveRoom(rooms[0].roomId);
      saveRelay(RELAY_SANKET);
      form.hidden = true;
      options();
      if (rooms.length) onChoose(relaySpec(RELAY_SANKET));
      else {
        error.textContent = "No channels assigned";
        error.hidden = false;
      }
    } catch (e) {
      error.textContent = e && e.status === 401 ? "Sign-in failed" : SANKET_UNREACHABLE;
      error.hidden = false;
    }
  }

  select.addEventListener("change", () => choose(select.value));
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    connect(email.value.trim(), password.value);
  });

  const saved = rememberedLogin();
  if (saved) {
    email.value = saved.email || "";
    password.value = saved.password || "";
    connect(email.value, password.value);
  } else if (getToken()) {
    assignedRooms().then((list) => {
      rooms = list;
      signedIn = true;
      if (!rooms.some((r) => r.roomId === loadRoom()) && rooms[0]) saveRoom(rooms[0].roomId);
      saveRelay(RELAY_SANKET);
      form.hidden = true;
      options();
    }).catch(() => { options(); });
  } else {
    options();
  }
  window.ptt2SetRelayRooms = (list, activeRoom) => {
    rooms = list || rooms;
    signedIn = true;
    if (activeRoom) saveRoom(activeRoom);
    form.hidden = true;
    options();
  };
  window.ptt2OnRelayNet = (event, relayId, channel) => {
    if (event === "unreachable" || event === "disconnected" || String(event || "").startsWith("unreachable")) {
      select.dataset.connection = "offline";
    } else {
      select.dataset.connection = "connected";
    }
    return "";
  };
}
