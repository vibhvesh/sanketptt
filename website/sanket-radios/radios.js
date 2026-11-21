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
  const actions = document.createElement("div");
  actions.className = "tile-actions";
  const open = document.createElement("a");
  open.className = "open";
  open.href = href;
  open.textContent = "Open radio";
  const copy = document.createElement("button");
  copy.type = "button";
  copy.textContent = "Copy share link";
  copy.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(href);
      copy.textContent = "Copied";
    } catch (e) {
      copy.textContent = "Copy failed";
    }
  });
  const share = document.createElement("a");
  share.className = "share";
  share.href = "https://wa.me/?text=" + encodeURIComponent(item.name + " " + href);
  share.target = "_blank";
  share.rel = "noopener";
  share.textContent = "WhatsApp";
  const native = document.createElement("button");
  native.type = "button";
  native.textContent = "Share";
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
  actions.append(open, copy, native, share);
  card.append(kind, title, detail, actions);
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
