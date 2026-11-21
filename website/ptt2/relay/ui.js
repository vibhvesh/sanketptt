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
    <label for="ptt2Channel">Channel</label>
    <select id="ptt2Channel"></select>
    <p class="ptt2-hint">Choose a channel to join. Sanket channels show up here after you are signed in.</p>
    <p id="ptt2RelayStatus"></p>
  `;
  const choice = root.querySelector("#ptt2Channel");
  const status = root.querySelector("#ptt2RelayStatus");
  let sanketRooms = [];

  function render() {
    const extra = loadPublicChannel();
    const publicRows = PUBLIC_CHANNELS.some((item) => item.id === extra)
      ? PUBLIC_CHANNELS
      : PUBLIC_CHANNELS.concat([{ id: extra, name: extra }]);
    const publicOpts = publicRows.map((item) => `<option value="public:${esc(item.id)}">${esc(item.name)}</option>`).join("");
    const sanketOpts = sanketRooms.map((item) => `<option value="sanket:${esc(item.roomId)}">${esc(item.roomName || item.roomId)}</option>`).join("");
    choice.innerHTML = `<optgroup label="Public">${publicOpts}</optgroup>`
      + (sanketOpts ? `<optgroup label="Sanket">${sanketOpts}</optgroup>` : "");
    const active = currentValue();
    if ([...choice.options].some((option) => option.value === active)) choice.value = active;
  }

  render();
  paint(status, loadRelay() === RELAY_SANKET ? "Joining " + loadRoom() + "." : "Joining " + loadPublicChannel() + ".");

  window.ptt2SetRelayRooms = (rooms) => {
    sanketRooms = rooms || [];
    render();
  };

  window.ptt2OnRelayNet = function (event, relayId, channel) {
    const text = formatRelayNet(event, relayId, channel);
    paint(status, text);
    return text;
  };

  choice.addEventListener("change", () => {
    const mark = choice.value.indexOf(":");
    const kind = choice.value.slice(0, mark);
    const id = choice.value.slice(mark + 1);
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
      return;
    }
    saveRelay(RELAY_PUBLIC);
    savePublicChannel(id);
    paint(status, "Joining " + id + ".");
    onChoose(relaySpec(RELAY_PUBLIC));
  });

  assignedRooms(loadAccount()).then((rooms) => {
    sanketRooms = rooms;
    render();
  }).catch(() => {
    if (loadRelay() === RELAY_SANKET) paint(status, SANKET_UNREACHABLE);
  });
}
