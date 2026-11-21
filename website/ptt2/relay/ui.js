import { RELAY_PUBLIC, RELAY_SANKET, SANKET_UNREACHABLE, formatRelayNet, loadRelay, saveRelay, relaySpec } from "./config.js";

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
    <p class="ptt2-hint">Public relays are the ones this radio uses today. The Sanket PTT relay address isn't confirmed yet.</p>
    <p id="ptt2RelayStatus"></p>
  `;
  const choice = root.querySelector("#ptt2RelayChoice");
  const status = root.querySelector("#ptt2RelayStatus");
  choice.value = current;
  paint(status, current === RELAY_SANKET ? "Connecting to the Sanket PTT relay." : "Connecting to the public relays.");

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
    paint(status, id === RELAY_SANKET ? "Connecting to the Sanket PTT relay." : "Connecting to the public relays.");
    onChoose(relaySpec(id));
  });
}
