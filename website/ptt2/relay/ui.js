import { RELAY_PUBLIC, RELAY_SANKET, SANKET_UNREACHABLE, formatRelayNet, loadRelay, loadRoom, saveRelay, saveRoom, relaySpec } from "./config.js";

function paint(status, text) {
  status.textContent = text;
  status.classList.toggle("down", text === SANKET_UNREACHABLE);
}

export function mountRelay(root, onChoose) {
  const current = loadRelay();
  root.innerHTML = `
    <h3>RELAY</h3>
    <label for="ptt2RelayChoice">Relay</label>
    <select id="ptt2RelayChoice">
      <option value="${RELAY_PUBLIC}">Public relays</option>
      <option value="${RELAY_SANKET}">Sanket PTT relay</option>
    </select>
    <p class="ptt2-hint">Public relays are the ones this radio uses today. Sanket PTT relay is relay.canberravision.com.</p>
    <label for="ptt2RelayRoom">Assigned channel</label>
    <select id="ptt2RelayRoom"></select>
    <p id="ptt2RelayStatus"></p>
  `;
  const choice = root.querySelector("#ptt2RelayChoice");
  const room = root.querySelector("#ptt2RelayRoom");
  const status = root.querySelector("#ptt2RelayStatus");
  choice.value = current;
  function showRooms(on) {
    room.hidden = !on;
    if (room.previousElementSibling) room.previousElementSibling.hidden = !on;
  }
  showRooms(current === RELAY_SANKET);
  room.innerHTML = `<option value="${loadRoom()}">${loadRoom()}</option>`;
  paint(status, current === RELAY_SANKET ? "Connecting to the Sanket PTT relay." : "Connecting to the public relays.");

  window.ptt2SetRelayRooms = (rooms, active) => {
    const assigned = (rooms || []).filter((item) => item && item.memberRole && item.roomId);
    if (!assigned.length) return;
    const esc = (value) => String(value).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
    room.innerHTML = assigned.map((item) => `<option value="${esc(item.roomId)}">${esc(item.roomName || item.roomId)}</option>`).join("");
    if (assigned.some((item) => item.roomId === active)) room.value = active;
  };

  window.ptt2OnRelayNet = function (event, relayId, channel) {
    const text = formatRelayNet(event, relayId, channel);
    paint(status, text);
    return text;
  };

  choice.addEventListener("change", () => {
    const id = saveRelay(choice.value);
    const url = new URL(location.href);
    url.searchParams.delete("relay");
    history.replaceState(null, "", url.pathname + url.search + url.hash);
    showRooms(id === RELAY_SANKET);
    paint(status, id === RELAY_SANKET ? "Connecting to the Sanket PTT relay." : "Connecting to the public relays.");
    onChoose(relaySpec(id));
  });
  room.addEventListener("change", () => {
    saveRoom(room.value);
    onChoose(relaySpec(RELAY_SANKET));
  });
}
