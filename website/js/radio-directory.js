/**
 * Live radio quick picks plus the optional verified directory.
 *
 * The five stations in the page are built in and stay playable if
 * ./data/radio-directory.json is missing, empty, or fails to load.
 * That file is produced by scripts/refresh_radio_directory.py. When the
 * refresh job cannot publish stations, this module says the directory is
 * unavailable and offers Retry instead of leaving "Directory status pending".
 */
(function () {
  const audio = document.getElementById("tafAudio");
  const select = document.getElementById("tafStationSelect");
  const play = document.getElementById("tafPlayBtn");
  const stop = document.getElementById("tafStopBtn");
  const nameEl = document.getElementById("tafNowName");
  const metaEl = document.getElementById("tafNowMeta");
  const status = document.getElementById("tafDirectoryStatus");
  const checked = document.getElementById("tafLastChecked");
  const retry = document.getElementById("directoryRetry");
  if (!audio || !select || !play || !stop) return;

  const STORE = "sanket.radio.preferences.v1";
  const BUILTIN = [
    { id: "bbc-world-service", name: "BBC World Service", region: "International", language: "English", url: "https://stream.live.vc.bbcmedia.co.uk/bbc_world_service", type: "mp3" },
    { id: "npr-news", name: "NPR News", region: "USA", language: "English", url: "https://npr-ice.streamguys1.com/live.mp3", type: "mp3" },
    { id: "vividh-bharati", name: "Vividh Bharati", region: "India", language: "Hindi", url: "https://radio.wavespb.com/live/146ed6ec6dea5a24/146ed6ec6dea5a24.m3u8", type: "hls" },
    { id: "fm-gold-delhi", name: "FM Gold Delhi", region: "India", language: "Hindi", url: "https://d3r9rhourdc02u.cloudfront.net/assets/radio/airdelhi03/air003_Auto.m3u8", type: "hls" },
    { id: "air-news", name: "AIR News 24×7", region: "India", language: "Hindi / English", url: "https://d3r9rhourdc02u.cloudfront.net/assets/radio/airdelhi01/air001_Auto.m3u8", type: "hls" }
  ];

  let current = null;
  let hls = null;
  let restored = null;
  const directory = [];

  function loadPrefs() {
    try { return JSON.parse(localStorage.getItem(STORE) || "{}"); }
    catch (e) { return {}; }
  }
  function savePrefs(patch) {
    try {
      const old = loadPrefs();
      localStorage.setItem(STORE, JSON.stringify(Object.assign({}, old, patch, { updatedAt: new Date().toISOString() })));
    } catch (e) {
      if (status) status.textContent = "Browser storage unavailable";
    }
  }

  function stopAudio() {
    audio.pause();
    audio.removeAttribute("src");
    audio.load();
    if (hls) { hls.destroy(); hls = null; }
    play.disabled = !current;
    stop.disabled = true;
    play.textContent = "▶ PLAY";
  }

  function find(id) {
    return BUILTIN.find((x) => x.id === id) || directory.find((x) => x.id === id);
  }

  function choose(st, remember) {
    if (!st) return;
    stopAudio();
    current = st;
    if (nameEl) nameEl.textContent = st.name;
    if (metaEl) metaEl.textContent = st.region + " · " + st.language;
    play.disabled = false;
    stop.disabled = false;
    document.querySelectorAll(".taf-top-five button").forEach((b) => {
      b.classList.toggle("active", b.dataset.station === st.id);
    });
    if (remember) savePrefs({ stationId: st.id });
  }

  function start() {
    if (!current) return;
    stopAudio();
    play.disabled = true;
    play.textContent = "CONNECTING…";
    const release = () => {
      play.textContent = "▶ PLAY";
      play.disabled = false;
      stop.disabled = false;
    };
    if (current.type === "hls" && window.Hls && window.Hls.isSupported()) {
      hls = new window.Hls({ enableWorker: true, lowLatencyMode: false });
      hls.loadSource(current.url);
      hls.attachMedia(audio);
      hls.on(window.Hls.Events.MANIFEST_PARSED, () => {
        audio.play().catch(() => {
          release();
          if (status) status.textContent = "Tap Play to start audio";
        });
      });
      hls.on(window.Hls.Events.ERROR, (_, d) => {
        if (d && d.fatal) {
          if (status) status.textContent = "Stream unavailable";
          stopAudio();
        }
      });
    } else {
      audio.src = current.url;
      audio.load();
      audio.play().catch(() => {
        release();
        if (status) status.textContent = "Tap Play to start audio";
      });
    }
    release();
  }

  document.querySelectorAll(".taf-top-five button").forEach((b) => {
    b.addEventListener("click", () => {
      const st = find(b.dataset.station);
      choose(st, true);
      start();
    });
  });
  play.addEventListener("click", () => start());
  stop.addEventListener("click", () => stopAudio());
  audio.addEventListener("playing", () => {
    play.textContent = "▶ PLAY";
    play.disabled = false;
    if (status) status.textContent = "Playing " + (current ? current.name : "");
  });
  audio.addEventListener("error", () => {
    if (status) status.textContent = "Stream could not be played";
    play.disabled = false;
  });

  const prefs = loadPrefs();
  audio.volume = Math.max(0, Math.min(1, Number(prefs.volume ?? 0.8)));
  audio.muted = !!prefs.muted;
  audio.addEventListener("volumechange", () => savePrefs({ volume: audio.volume, muted: audio.muted }));

  function showDirectoryUnavailable(detail) {
    if (status) status.textContent = "Directory unavailable";
    if (checked) checked.textContent = detail || "Showing built-in stations";
    if (retry) retry.hidden = false;
  }

  function renderDirectory(data) {
    const extra = (data || []).filter((x) => x && x.id && x.url && !BUILTIN.some((c) => c.id === x.id));
    directory.splice(0, directory.length, ...extra);
    select.innerHTML = "";
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = extra.length ? "More stations…" : "Built-in stations only";
    select.append(placeholder);
    extra.forEach((st) => {
      const o = document.createElement("option");
      o.value = st.id;
      o.textContent = st.name + " · " + (st.region || "");
      select.append(o);
    });
    if (restored) {
      const st = find(restored);
      if (st) choose(st, false);
      restored = null;
    }
  }

  select.addEventListener("change", () => {
    const st = find(select.value);
    if (st) {
      choose(st, true);
      start();
      select.value = "";
    }
  });

  restored = prefs.stationId || null;
  if (restored) {
    const st = find(restored);
    if (st) choose(st, false);
    else if (nameEl) {
      nameEl.textContent = "Restoring last station…";
      if (metaEl) metaEl.textContent = "Waiting for station directory";
    }
  }

  async function refresh() {
    if (status) status.textContent = "Checking stations…";
    if (retry) retry.hidden = true;
    try {
      const r = await fetch("./data/radio-directory.json?t=" + Date.now(), { cache: "no-store" });
      if (!r.ok) throw new Error("directory " + r.status);
      const j = await r.json();
      const stations = Array.isArray(j.stations) ? j.stations : [];
      renderDirectory(stations);
      if (!stations.length) {
        showDirectoryUnavailable("Showing built-in stations");
        return;
      }
      const when = j.generated_at ? new Date(j.generated_at) : new Date();
      const stamp = Number.isNaN(when.getTime()) ? "" : when.toLocaleString();
      if (status) status.textContent = "Directory updated";
      if (checked) checked.textContent = stamp ? "Updated " + stamp : "Verified directory loaded";
      if (retry) retry.hidden = true;
    } catch (e) {
      renderDirectory([]);
      showDirectoryUnavailable("Showing built-in stations");
    }
  }

  if (retry) retry.addEventListener("click", () => { refresh(); });
  refresh();
  setInterval(refresh, 15 * 60 * 1000);
})();
