import {
  PUBLIC_CHANNELS, RELAY_PUBLIC, RELAY_SANKET, SANKET_UNREACHABLE,
  loadPublicChannel, loadRelay, loadRoom, relaySpec, savePublicChannel, saveRelay, saveRoom,
} from "./config.js";
import { assignedRooms, listFreeRooms } from "./sanket-socket.js";
import { getToken, rememberedLogin, signIn, signOut } from "./auth.js";

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

export function mountRelay(root, onChoose, onSwitchOff = () => {}) {
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
    <button type="button" id="ptt2PowerOff" aria-label="Switch off radio" hidden>
      <span class="ptt2-power-led"></span><span class="ptt2-power-symbol">⏻</span><span class="ptt2-power-label">OFF</span>
    </button>
  `;
  const select = root.querySelector("#ptt2Frequency");
  const form = root.querySelector("#ptt2Auth");
  const email = root.querySelector("#ptt2Email");
  const password = root.querySelector("#ptt2Password");
  const error = root.querySelector("#ptt2AuthError");
  const power = root.querySelector("#ptt2PowerOff");
  let rooms = [];
  let signedIn = false;
  let active = false;

  function options() {
    const items = rooms.map((r) => ({ value: "sanket:" + r.roomId, name: r.roomName || r.name || r.roomId }));
    const selected = currentValue();
    select.innerHTML = items.map((item) =>
      '<option value="' + esc(item.value) + '"' + (item.value === selected ? " selected" : "") + ">" + esc(item.name) + "</option>"
    ).join("");
    select.hidden = false;
    select.disabled = !signedIn || items.length < 2;
  }

  async function loadRooms() {
    const [assigned, free] = await Promise.all([
      assignedRooms().catch(() => []),
      listFreeRooms().catch(() => []),
    ]);
    const unique = new Map();
    [...assigned, ...free].forEach((room) => {
      if (room && room.roomId) unique.set(room.roomId, room);
    });
    rooms = [...unique.values()];
    if (!rooms.some((r) => r.roomId === loadRoom()) && rooms[0]) saveRoom(rooms[0].roomId);
    return rooms;
  }

  function setPower(on) {
    active = !!on;
    power.hidden = false;
    power.classList.toggle("is-on", active);
    power.classList.toggle("is-off", !active);
    power.querySelector(".ptt2-power-label").textContent = active ? "ON" : "OFF";
    power.setAttribute("aria-label", active ? "Switch off radio" : "Radio is off");
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
      await loadRooms();
      signedIn = true;
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
      signedIn = false;
      setPower(false);
    }
  }

  select.addEventListener("change", () => choose(select.value));
  power.addEventListener("click", () => {
    if (!active) return;
    setPower(false);
    onSwitchOff();
    signOut();
    signedIn = false;
    form.hidden = false;
    options();
  });
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
    loadRooms().then(() => {
      signedIn = true;
      if (!rooms.some((r) => r.roomId === loadRoom()) && rooms[0]) saveRoom(rooms[0].roomId);
      saveRelay(RELAY_SANKET);
      form.hidden = true;
      options();
    }).catch(() => { options(); });
  } else {
    options();
  }
  setPower(false);
  window.ptt2SetRelayRooms = async (list, activeRoom) => {
    await loadRooms();
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
      if (signedIn) setPower(true);
    }
    return "";
  };
}
