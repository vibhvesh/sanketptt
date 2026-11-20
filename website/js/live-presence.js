/**
 * Live relay and presence for the public demo channel (virtual).
 *
 * Uses the same public MQTT brokers as the Sanket PTT client.
 * Checked from this repo's network: public.cloud.shiftr.io, broker.emqx.io
 * and test.mosquitto.org complete an MQTT CONNACK. broker.hivemq.com accepts
 * the websocket upgrade and then never sends CONNACK, so it is omitted —
 * leaving it in the list held the panel on "connecting".
 *
 * If the MQTT library cannot load, or every broker fails its deadline, the
 * panels switch to an explicit offline state with Retry. They do not stay
 * on "connecting".
 */
(function () {
  const PREFIX = "ptt-radio-66ab9178/";
  const CHANNEL = "virtual";
  const ROOT = PREFIX + CHANNEL + "/";
  const BROKERS = [
    "wss://public:public@public.cloud.shiftr.io",
    "wss://broker.emqx.io:8084/mqtt",
    "wss://test.mosquitto.org:8081"
  ];
  const ATTEMPT_MS = 4500;
  const MQTT_SRC = "https://unpkg.com/mqtt@5/dist/mqtt.min.js";

  const $ = (id) => document.getElementById(id);
  const users = new Map();
  const history = [];
  const seen = new Set();
  let client = null;
  let attempt = 0;
  let generation = 0;
  let live = false;

  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[c]));
  const clock = (t) => new Date(t || Date.now()).toLocaleTimeString([], {
    hour: "2-digit", minute: "2-digit", second: "2-digit"
  });

  function setSignal(id, state, label) {
    const el = $(id);
    if (!el) return;
    el.classList.remove("good", "active", "bad");
    if (state) el.classList.add(state);
    const target = el.querySelector("small");
    if (target && label != null) target.textContent = label;
  }

  function event(type, name, detail) {
    history.unshift({ type, name, detail, ts: Date.now() });
    history.splice(30);
    renderHistory();
  }

  function renderHistory() {
    const host = $("userHistory");
    if (!host) return;
    if (!history.length) {
      host.innerHTML = '<p class="empty-live">No join or leave events in this page session yet.</p>';
      return;
    }
    host.innerHTML = history.map((e) =>
      '<div class="presence-event"><b>' + esc(e.type) + "</b> · " + esc(e.name) +
      "<small>" + esc(e.detail || "") + " · " + clock(e.ts) + "</small></div>"
    ).join("");
  }

  function renderUsers() {
    const list = [...users.values()].sort((a, b) => a.name.localeCompare(b.name));
    const count = $("presenceCount");
    if (count) count.textContent = String(list.length);
    if (live) {
      setSignal("sigUsers", list.length ? "good" : "", list.length ? list.length + " ONLINE" : "NONE ONLINE");
    }
    const host = $("connectedUsers");
    if (!host) return;
    host.innerHTML = list.length
      ? list.map((u) => '<div class="presence-user"><b>● ' + esc(u.name) + "</b><small>Seen " +
          clock(u.lastSeen) + " · " + esc(u.id.slice(0, 10)) + "</small></div>").join("")
      : (live
        ? '<p class="empty-live">Relay is live. No stations are online on this channel right now.</p>'
        : host.innerHTML);
  }

  function transcript(m) {
    if (!m || !m.text) return;
    setSignal("sigTranscript", "good", "LAST: " + clock(+m.ts || Date.now()));
    const id = String(m.id || "");
    if (id && seen.has(id)) return;
    if (id) {
      seen.add(id);
      if (seen.size > 300) seen.delete(seen.values().next().value);
    }
    const el = document.createElement("article");
    el.className = "transcript-event";
    const meta = document.createElement("div");
    meta.className = "event-meta";
    const who = document.createElement("span");
    who.className = "event-speaker";
    who.textContent = m.speaker || "PTT user";
    const tm = document.createElement("span");
    tm.textContent = clock(+m.ts || Date.now()) + " · " + (m.language || "language n/a");
    meta.append(who, tm);
    const body = document.createElement("div");
    body.className = "event-text";
    body.textContent = m.text;
    el.append(meta, body);
    if (m.translation) {
      const tr = document.createElement("div");
      tr.className = "event-translation";
      tr.textContent = "Translation: " + m.translation;
      el.append(tr);
    }
    const ch = document.createElement("div");
    ch.className = "event-meta";
    ch.style.marginTop = "7px";
    ch.textContent = "CHANNEL " + (m.channel || CHANNEL) + " · " + (m.source || "Sanket Transcribe");
    el.append(ch);
    const feed = $("liveMessageFeed");
    if (!feed) return;
    const empty = feed.querySelector(".empty-live");
    if (empty) empty.remove();
    feed.prepend(el);
    while (feed.children.length > 25) feed.lastElementChild.remove();
  }

  function onMessage(topic, payload) {
    const suffix = topic.slice(ROOT.length);
    const raw = payload.toString();
    const now = Date.now();
    if (suffix === "audio") {
      setSignal("sigRx", "active", "AUDIO " + clock(now));
      return;
    }
    if (suffix.startsWith("presence/")) {
      const id = suffix.slice(9);
      if (!raw) {
        const old = users.get(id);
        if (old) {
          users.delete(id);
          event("LEFT", old.name, "Disconnected from " + CHANNEL);
          renderUsers();
        }
        return;
      }
      try {
        const m = JSON.parse(raw);
        if (!m.id || !m.name) return;
        const old = users.get(id);
        users.set(id, { id, name: String(m.name).slice(0, 40), lastSeen: now });
        if (!old) event("JOINED", String(m.name).slice(0, 40), "Connected to " + CHANNEL);
        renderUsers();
      } catch (e) { /* ignore malformed presence */ }
      return;
    }
    if (suffix === "transcript") {
      try {
        const m = JSON.parse(raw);
        transcript(m);
        if (m && m.speaker) event("TRANSCRIBED", String(m.speaker).slice(0, 40), String(m.text || "").slice(0, 100));
      } catch (e) { /* ignore */ }
    }
    if (suffix === "floor") {
      try {
        const m = JSON.parse(raw);
        if (m.t === "claim") {
          event("TRANSMITTING", m.name || "PTT user", "Floor claimed on " + CHANNEL);
          setSignal("sigTx", "active", String(m.name || "STATION") + " TX");
        }
        if (m.t === "release") {
          event("TX ENDED", m.name || "PTT user", "Floor released on " + CHANNEL);
          setSignal("sigTx", "", "IDLE");
        }
      } catch (e) { /* ignore */ }
    }
  }

  function setRetryVisible(on) {
    const btn = $("presenceRetry");
    if (btn) btn.hidden = !on;
  }

  function showOffline() {
    live = false;
    const state = $("presenceState");
    if (state) state.textContent = "OFFLINE";
    setSignal("sigRelay", "bad", "OFFLINE");
    setSignal("sigUsers", "bad", "UNAVAILABLE");
    const host = $("connectedUsers");
    if (host) {
      host.innerHTML = '<p class="empty-live">Presence relay is unavailable. Retry, or use the page without live presence.</p>';
    }
    setRetryVisible(true);
  }

  function loadMqtt() {
    if (window.mqtt && typeof window.mqtt.connect === "function") return Promise.resolve(window.mqtt);
    return new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = MQTT_SRC;
      s.async = true;
      s.onload = () => (window.mqtt && typeof window.mqtt.connect === "function")
        ? resolve(window.mqtt)
        : reject(new Error("mqtt global missing"));
      s.onerror = () => reject(new Error("mqtt library failed to load"));
      document.head.appendChild(s);
    });
  }

  function connect() {
    const gen = ++generation;
    live = false;
    setRetryVisible(false);
    setSignal("sigRelay", "", "CONNECTING");
    const state = $("presenceState");
    if (state) state.textContent = "CONNECTING…";

    loadMqtt().then((mqtt) => {
      if (gen !== generation) return;
      const url = BROKERS[attempt % BROKERS.length];
      let settled = false;
      let expectClose = false;
      const c = mqtt.connect(url, {
        clientId: "sanket_web_" + Math.random().toString(36).slice(2, 12),
        clean: true,
        keepalive: 20,
        reconnectPeriod: 0,
        connectTimeout: ATTEMPT_MS
      });
      client = c;
      const timer = setTimeout(() => giveUp(), ATTEMPT_MS + 400);

      function giveUp() {
        if (settled || gen !== generation) return;
        settled = true;
        expectClose = true;
        clearTimeout(timer);
        try { c.end(true); } catch (e) { /* already closed */ }
        if (client === c) client = null;
        attempt += 1;
        if (attempt >= BROKERS.length) {
          attempt = 0;
          showOffline();
          return;
        }
        connect();
      }

      c.on("connect", () => {
        if (gen !== generation) {
          expectClose = true;
          try { c.end(true); } catch (e) { /* ignore */ }
          return;
        }
        settled = true;
        clearTimeout(timer);
        live = true;
        attempt = 0;
        if (state) state.textContent = "LIVE";
        setSignal("sigRelay", "good", "CONNECTED");
        setRetryVisible(false);
        c.subscribe([ROOT + "presence/+", ROOT + "transcript", ROOT + "floor", ROOT + "audio"]);
        renderUsers();
      });
      c.on("message", onMessage);
      c.on("error", () => { if (!settled) giveUp(); });
      c.on("close", () => {
        if (expectClose || gen !== generation) return;
        if (!settled) {
          giveUp();
          return;
        }
        live = false;
        users.clear();
        if (state) state.textContent = "RECONNECTING";
        setSignal("sigRelay", "bad", "RECONNECTING");
        renderUsers();
        setTimeout(() => {
          if (generation !== gen) return;
          attempt = 0;
          connect();
        }, 1200);
      });
    }).catch(() => {
      if (gen !== generation) return;
      showOffline();
    });
  }

  function retry() {
    const old = client;
    client = null;
    attempt = 0;
    users.clear();
    connect();
    if (old) {
      try { old.end(true); } catch (e) { /* ignore */ }
    }
  }

  const retryBtn = $("presenceRetry");
  if (retryBtn) retryBtn.addEventListener("click", retry);

  setInterval(() => {
    if (!live) return;
    const now = Date.now();
    for (const [id, u] of users) {
      if (now - u.lastSeen > 16000) {
        users.delete(id);
        event("TIMED OUT", u.name, "Presence heartbeat expired");
      }
    }
    renderUsers();
  }, 3000);

  renderHistory();
  setSignal("sigRelay", "", "CONNECTING");
  setSignal("sigUsers", "", "CHECKING");
  setSignal("sigTx", "", "IDLE");
  setSignal("sigRx", "", "WAITING");
  setSignal("sigTranscript", "", "WAITING");
  const state = $("presenceState");
  if (state) state.textContent = "CONNECTING…";
  connect();
})();
