import { PUBLIC_CHANNELS } from "../ptt2/relay/config.js";
import { ensureGuest } from "./guest.js";
import { listFreeRooms } from "../ptt2/relay/sanket-socket.js";

const grid = document.querySelector("#radioTiles");
const status = document.querySelector("#radioStatus");

function radioHref(id) {
  const url = new URL("../ptt2/", location.href);
  url.search = "";
  url.searchParams.set("free", "1");
  url.searchParams.set("ch", id);
  return url.toString();
}

function icon(name) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  const d = {
    copy: "M8 7V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2h-2M6 7h8a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V9a2 2 0 0 1 2-2z",
    share: "M12 3v12m0-12 4 4m-4-4-4 4M5 14v5a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-5",
    whatsapp: "M5 19.5 6.2 16A8 8 0 1 1 8.5 18.2L5 19.5z",
  };
  path.setAttribute("d", d[name]);
  path.setAttribute("fill", "none");
  path.setAttribute("stroke", "currentColor");
  path.setAttribute("stroke-width", "1.8");
  path.setAttribute("stroke-linecap", "round");
  path.setAttribute("stroke-linejoin", "round");
  svg.append(path);
  return svg;
}

function toolButton(iconName, label) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "tool";
  const text = document.createElement("span");
  text.textContent = label;
  button.append(icon(iconName), text);
  return button;
}

function tile(item) {
  const href = radioHref(item.id);
  const card = document.createElement("article");
  card.className = "radio-tile";
  const title = document.createElement("b");
  title.textContent = item.name;
  const kind = document.createElement("span");
  kind.className = "kind";
  kind.textContent = item.kind;
  const detail = document.createElement("small");
  detail.textContent = item.id;
  const head = document.createElement("div");
  head.className = "tile-head";
  head.append(kind, title, detail);
  const actions = document.createElement("div");
  actions.className = "tile-actions";
  const open = document.createElement("a");
  open.className = "open";
  open.href = href;
  open.textContent = "Open radio";
  const tools = document.createElement("div");
  tools.className = "tile-tools";
  const copy = toolButton("copy", "Copy");
  copy.addEventListener("click", async () => {
    const label = copy.querySelector("span");
    try {
      await navigator.clipboard.writeText(href);
      label.textContent = "Copied";
    } catch (e) {
      label.textContent = "Failed";
    }
  });
  const share = document.createElement("a");
  share.className = "tool share";
  share.href = "https://wa.me/?text=" + encodeURIComponent(item.name + " " + href);
  share.target = "_blank";
  share.rel = "noopener";
  share.append(icon("whatsapp"), Object.assign(document.createElement("span"), { textContent: "WhatsApp" }));
  const native = toolButton("share", "Share");
  native.addEventListener("click", async () => {
    if (navigator.share) {
      try {
        await navigator.share({ title: item.name, text: item.name, url: href });
        return;
      } catch (e) {
        if (e && e.name === "AbortError") return;
      }
    }
    share.click();
  });
  tools.append(copy, native, share);
  actions.append(open, tools);
  card.append(head, actions);
  return card;
}

function paint(items) {
  grid.replaceChildren(...items.map(tile));
}

const mqtt = PUBLIC_CHANNELS.map((item) => ({ id: item.id, name: item.name, kind: "Public radio" }));

async function load() {
  paint(mqtt);
  status.textContent = "Loading free relay rooms…";
  try {
    await ensureGuest();
    const rooms = await listFreeRooms();
    const relay = rooms.map((room) => ({
      id: room.roomId,
      name: room.roomName || room.roomId,
      kind: "Free relay room",
    }));
    paint([...relay, ...mqtt]);
    status.textContent = relay.length ? relay.length + " free relay rooms, plus the public radio channels." : "No password-free relay rooms. Public radio channels are listed below.";
  } catch (e) {
    status.textContent = "Free relay rooms could not be loaded. Public radio channels are still available.";
  }
}

load();
