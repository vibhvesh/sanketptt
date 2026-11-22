import { RELAY_SANKET, SANKET_UNREACHABLE, formatRelayNet, relaySpec, saveRoom } from "./config.js";
import { assignedRooms } from "./sanket-socket.js";
import { getToken, rememberedLogin, signIn, signOut } from "./auth.js";

function paint(status, message) {
  if (!status) return;
  status.textContent = message;
  status.classList.toggle("down", message === SANKET_UNREACHABLE);
}

function esc(value) {
  return String(value).replace(/[&<>"]/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"
  }[ch]));
}

export function mountRelay(root, onChoose) {
  root.innerHTML = `
    <h3>SANKET RELAY CHANNELS</h3>
    <div id="ptt2ChannelChips" role="listbox" aria-label="Your Sanket channels">
      <p class="ptt2-hint">Sign in to load your authorized channels.</p>
    </div>
    <form id="ptt2Auth">
      <label for="ptt2Email">Email</label>
      <input id="ptt2Email" type="email" autocomplete="username" inputmode="email" required>
      <label for="ptt2Password">Password</label>
      <div class="ptt2-pass">
        <input id="ptt2Password" type="password" autocomplete="current-password" required>
        <button type="button" id="ptt2PassToggle">Show</button>
      </div>
      <label class="ptt2-remember"><input id="ptt2Remember" type="checkbox"> Remember me</label>
      <button type="submit" id="ptt2SignIn">Sign in to Sanket</button>
      <p id="ptt2AuthError" hidden></p>
    </form>
    <button type="button" id="ptt2SignOut" hidden>Sign out</button>
    <p id="ptt2RelayStatus">Not connected</p>
  `;

  const chips = root.querySelector("#ptt2ChannelChips");
  const form = root.querySelector("#ptt2Auth");
  const email = root.querySelector("#ptt2Email");
  const password = root.querySelector("#ptt2Password");
  const remember = root.querySelector("#ptt2Remember");
  const toggle = root.querySelector("#ptt2PassToggle");
  const error = root.querySelector("#ptt2AuthError");
  const signOutButton = root.querySelector("#ptt2SignOut");
  const status = root.querySelector("#ptt2RelayStatus");
  let rooms = [];
  let activeRoom = "";

  function showError(message) {
    error.hidden = !message;
    error.textContent = message || "";
  }

  function render() {
    if (!rooms.length) {
      chips.innerHTML = '<p class="ptt2-hint">No channels have been assigned to this account.</p>';
    } else {
      chips.innerHTML = rooms.map((room) => {
        const id = String(room.roomId || "");
        const name = String(room.roomName || room.name || id);
        const selected = id === activeRoom;
        return '<button type="button" class="ptt2-chip' + (selected ? ' is-on' : '') +
          '" data-room="' + esc(id) + '" aria-pressed="' + (selected ? 'true' : 'false') +
          '">' + esc(name) + '</button>';
      }).join("");
    }
    form.hidden = !!getToken();
    signOutButton.hidden = !getToken();
  }

  function connectRoom(roomId) {
    const room = rooms.find((item) => item.roomId === roomId);
    if (!room) return;
    activeRoom = roomId;
    saveRoom(roomId);
    render();
    paint(status, "Connecting to " + (room.roomName || room.name || roomId) + "…");
    onChoose(relaySpec(roomId));
  }

  async function enter(address, secret, keep) {
    showError("");
    paint(status, "Signing in to Sanket Relay…");
    try {
      await signIn(address, secret, keep);
      rooms = await assignedRooms();
      render();
      if (!rooms.length) {
        showError("Your Sanket account has no assigned channels. Contact your administrator.");
        paint(status, "Signed in · no assigned channels");
        return;
      }
      const preferred = rooms.find((room) => room.roomId === activeRoom) ||
        rooms.find((room) => room.roomId === localStorage.getItem("sanket.ptt2.relayRoom")) ||
        rooms[0];
      connectRoom(preferred.roomId);
    } catch (e) {
      rooms = [];
      render();
      if (e && e.status === 401) showError("Sign-in failed. Check your email and password.");
      else showError(e && e.message ? e.message : "Could not reach Sanket Relay.");
      paint(status, SANKET_UNREACHABLE);
    }
  }

  chips.addEventListener("click", (event) => {
    const button = event.target.closest("[data-room]");
    if (button) connectRoom(button.getAttribute("data-room"));
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    enter(email.value, password.value, remember.checked);
  });

  toggle.addEventListener("click", () => {
    const show = password.type === "password";
    password.type = show ? "text" : "password";
    toggle.textContent = show ? "Hide" : "Show";
  });

  signOutButton.addEventListener("click", () => {
    if (typeof window.ptt2StopRelay === "function") window.ptt2StopRelay();
    signOut();
    rooms = [];
    activeRoom = "";
    saveRoom("");
    password.value = "";
    render();
    paint(status, "Signed out of Sanket Relay");
  });

  window.ptt2SetRelayRooms = (available, selectedRoom) => {
    rooms = (available || []).filter((room) => room && room.roomId);
    if (selectedRoom) activeRoom = selectedRoom;
    render();
  };

  window.ptt2OnRelayNet = function (event, relayId, channel) {
    const message = formatRelayNet(event, relayId, channel);
    paint(status, message);
    render();
    return message;
  };

  const saved = rememberedLogin();
  render();
  if (saved && !getToken()) {
    email.value = saved.email;
    password.value = saved.password;
    remember.checked = true;
  }
  if (getToken() && saved) {
    enter(saved.email, saved.password, true);
  }
}
