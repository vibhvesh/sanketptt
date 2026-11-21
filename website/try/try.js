import { pairs, pairEmbed, pairListen, pairOpen, transcribeFor, mqttTopic } from "../ptt/links.js";

const root = document.getElementById("pairs");
const tabs = document.getElementById("tabs");

function pane(title, src, label) {
  const box = document.createElement("div");
  box.className = "pane";
  const h = document.createElement("h3");
  h.textContent = title;
  const frame = document.createElement("iframe");
  frame.title = label;
  frame.loading = "lazy";
  frame.setAttribute("allow", "microphone; autoplay");
  frame.referrerPolicy = "strict-origin-when-cross-origin";
  frame.dataset.src = src;
  box.append(h, frame);
  return box;
}

function card(pair) {
  const article = document.createElement("article");
  article.className = "card";
  article.id = "pair-" + pair.id;
  const h = document.createElement("h2");
  h.textContent = pair.title;
  const meta = document.createElement("p");
  meta.className = "meta";
  meta.textContent = pair.status === "none"
    ? "No live audio feed for transcription."
    : "Status: " + pair.status + " pair.";
  const how = document.createElement("p");
  how.className = "how";
  how.textContent = "Open this channel on a second phone, press and hold to talk, and watch the words appear here.";
  const actions = document.createElement("div");
  actions.className = "actions";
  const open = document.createElement("a");
  open.className = "primary";
  open.href = pairOpen(pair);
  open.target = "_blank";
  open.rel = "noopener";
  open.textContent = "Open full screen";
  actions.append(open);
  if (pair.status !== "none") {
    const listen = document.createElement("a");
    listen.href = transcribeFor(pair.channel);
    listen.target = "_blank";
    listen.rel = "noopener";
    listen.textContent = "Open transcriber";
    actions.append(listen);
  }
  const grid = document.createElement("div");
  grid.className = "pair";
  if (pair.status === "none") {
    const left = document.createElement("div");
    left.className = "pane";
    const lh = document.createElement("h3");
    lh.textContent = "PANEL";
    const frame = document.createElement("iframe");
    frame.title = pair.title;
    frame.loading = "lazy";
    frame.dataset.src = pairEmbed(pair);
    left.append(lh, frame);
    const right = document.createElement("div");
    right.className = "pane";
    const rh = document.createElement("h3");
    rh.textContent = "TRANSCRIPTION";
    const note = document.createElement("p");
    note.className = "soon";
    note.textContent = "Transcription coming soon. " + pair.note;
    right.append(rh, note);
    grid.append(left, right);
  } else {
    grid.append(
      pane("PUSH TO TALK", pairEmbed(pair), pair.title + " push to talk"),
      pane("LIVE TRANSCRIPTION", pairListen(pair), pair.title + " transcription")
    );
  }
  const topic = document.createElement("p");
  topic.className = "topic";
  topic.textContent = pair.channel
    ? "Relay " + mqttTopic(pair.channel) + "audio · " + pair.note
    : pair.note;
  article.append(h, meta, how, actions, grid, topic);
  return article;
}

const cards = pairs.map(card);
cards.forEach((el) => root.append(el));

pairs.forEach((pair, i) => {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = pair.title;
  button.setAttribute("aria-selected", i === 0 ? "true" : "false");
  button.addEventListener("click", () => {
    tabs.querySelectorAll("button").forEach((b) => b.setAttribute("aria-selected", "false"));
    button.setAttribute("aria-selected", "true");
    cards[i].scrollIntoView({ behavior: "smooth", block: "start" });
    load(cards[i]);
  });
  tabs.append(button);
});

function load(cardEl) {
  cardEl.querySelectorAll("iframe[data-src]").forEach((frame) => {
    if (!frame.src) frame.src = frame.dataset.src;
  });
}

const seen = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (!entry.isIntersecting) return;
    load(entry.target);
    seen.unobserve(entry.target);
  });
}, { rootMargin: "200px" });
cards.forEach((el) => seen.observe(el));
load(cards[0]);
