import { SANKET_TRANSCRIBE_SERVER, SERVER_CUSTOM, SERVER_SANKET, loadConfig, saveConfig, isAllowedServer } from "./config.js";
import { localCapability, serverHealthy } from "./detect.js";
import { transcribeTransmission } from "./router.js";
import { lineFromRadio } from "./line.js";

const notes = new Map();

function escapeText(value) {
  return String(value).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
}

function lineHtml(note, key) {
  if (!note || note.pending) return '<span class="ptt2-badge wait">…</span> transcribing';
  if (note.skipped) return '<span class="ptt2-badge wait">too short</span> too short';
  if (note.failed) {
    return '<span class="ptt2-badge local">failed</span> transcription failed <button type="button" class="ptt2-retry" data-retry="' + key + '">Retry</button>';
  }
  const label = note.source === "server" ? "server" : "local";
  const text = note.text ? escapeText(note.text) : "(no speech)";
  const extra = note.note ? `<span class="ptt2-note">${escapeText(note.note)}</span>` : "";
  return `<span class="ptt2-badge ${label}">${label}</span> ${text}${extra}`;
}

export function decorateLog(entries) {
  const log = document.getElementById("log");
  if (!log || !entries) return;
  entries.forEach((entry) => {
    const button = log.querySelector(`button[data-k="${entry.key}"]`);
    if (!button) return;
    const item = button.closest("li");
    if (!item) return;
    let line = item.querySelector(".ptt2-line");
    if (!line) {
      line = document.createElement("div");
      line.className = "ptt2-line";
      item.append(line);
    }
    line.innerHTML = lineHtml(notes.get(entry.key), entry.key);
  });
}

const clips = new Map();
const SAFETY_MS = 50000;

function remember(key, wav) {
  clips.set(key, wav);
  if (clips.size > 30) clips.delete(clips.keys().next().value);
}

function applyResult(recorder, key, result) {
  notes.set(key, {
    pending: false,
    skipped: !!result.skipped,
    failed: !!result.failed,
    source: result.source,
    text: result.text || "",
    note: result.note || "",
  });
  decorateLog(recorder.entries);
  if (result.note && !result.skipped) {
    const status = document.getElementById("ptt2Status");
    if (status) status.textContent = result.note;
  }
}

function startJob(recorder, key, wav, line) {
  notes.set(key, { pending: true });
  decorateLog(recorder.entries);
  let settled = false;
  const finish = (result) => {
    if (settled) return;
    settled = true;
    applyResult(recorder, key, result);
  };
  const watchdog = setTimeout(() => finish({ failed: true, text: "transcription failed", note: "timed out" }), SAFETY_MS);
  transcribeTransmission(wav, line).then((result) => {
    clearTimeout(watchdog);
    finish(result || { failed: true, text: "transcription failed" });
  }).catch((error) => {
    clearTimeout(watchdog);
    finish({ failed: true, text: "transcription failed", note: error && error.message ? error.message : "" });
  });
}

export function watchRecorder(recorder, renderLog) {
  const log = document.getElementById("log");
  if (log && !log.dataset.ptt2Retry) {
    log.dataset.ptt2Retry = "1";
    log.addEventListener("click", (event) => {
      const button = event.target.closest("[data-retry]");
      if (!button) return;
      event.preventDefault();
      event.stopPropagation();
      const key = Number(button.getAttribute("data-retry"));
      const wav = clips.get(key);
      if (!wav) return;
      startJob(recorder, key, wav, lineFromRadio(globalThis.radio, { mine: true, name: globalThis.radio && globalThis.radio.name, id: globalThis.radio && globalThis.radio.id }));
    }, true);
  }
  const originalEnd = recorder.end.bind(recorder);
  recorder.end = function () {
    const entry = originalEnd();
    if (entry && entry.wav) {
      remember(entry.key, entry.wav);
      startJob(recorder, entry.key, entry.wav, lineFromRadio(globalThis.radio, entry));
    }
    return entry;
  };
  recorder.onChange = function (entries) {
    renderLog(entries);
    decorateLog(entries);
  };
}

export function mountSettings(root) {
  const config = loadConfig();
  root.hidden = true;
  root.innerHTML = `
    <div class="ptt2-settings-head"><h3>RADIO SETTINGS &amp; DIAGNOSTICS</h3><button type="button" id="ptt2SettingsClose" aria-label="Close settings">×</button></div>
    <label for="ptt2Mode">Transcription engine</label>
    <select id="ptt2Mode"><option value="auto">Auto · server first, local fallback</option><option value="server">Server only</option><option value="local">Local only</option></select>
    <label for="ptt2ServerChoice">Server</label>
    <select id="ptt2ServerChoice"><option value="sanket">Sanket Transcribe (default)</option><option value="custom">Custom URL…</option></select>
    <label for="ptt2Server" id="ptt2ServerLabel" hidden>Custom URL</label>
    <input id="ptt2Server" type="url" placeholder="https://…" autocomplete="off" hidden>
    <label for="ptt2Language">Speech language</label>
    <select id="ptt2Language"><option value="auto">Auto detect / channel default</option><option value="en">English</option><option value="hi">Hindi</option><option value="gu">Gujarati</option><option value="mr">Marathi</option><option value="bn">Bengali</option><option value="pa">Punjabi</option><option value="ta">Tamil</option><option value="te">Telugu</option><option value="ur">Urdu</option><option value="zh">Chinese</option><option value="ru">Russian</option></select>
    <div class="ptt2-setting-check"><input id="ptt2Translate" type="checkbox"><label for="ptt2Translate">Translate transcription</label></div>
    <label for="ptt2TargetLanguage">Destination language (local translation)</label>
    <select id="ptt2TargetLanguage"><option value="en">English</option><option value="hi">Hindi</option><option value="gu">Gujarati</option><option value="mr">Marathi</option><option value="bn">Bengali</option><option value="pa">Punjabi</option><option value="ta">Tamil</option><option value="te">Telugu</option><option value="ur">Urdu</option><option value="zh">Chinese</option><option value="ru">Russian</option></select>
    <p class="ptt2-hint">Local translation downloads a multilingual model on first use and caches it in this browser. The first download can be large.</p>
    <div class="ptt2-report"><b>STARTUP CHECK / REPORT</b><p id="ptt2Status">Checking server and local capability…</p><button type="button" id="ptt2RunCheck">Run check again</button></div>
  `;
  const $ = (selector) => root.querySelector(selector);
  const mode=$("#ptt2Mode"), choice=$("#ptt2ServerChoice"), serverLabel=$("#ptt2ServerLabel"), server=$("#ptt2Server");
  const language=$("#ptt2Language"), translate=$("#ptt2Translate"), target=$("#ptt2TargetLanguage"), status=$("#ptt2Status");
  mode.value=config.mode; choice.value=config.serverChoice===SERVER_CUSTOM?SERVER_CUSTOM:SERVER_SANKET;
  server.value=config.serverChoice===SERVER_CUSTOM?config.serverUrl:"";
  language.value=config.language||"auto"; translate.checked=!!config.translate; target.value=config.targetLanguage||"hi";
  $("#ptt2SettingsClose").addEventListener("click",()=>{root.hidden=true;const b=document.getElementById("ptt2SettingsToggle");if(b)b.setAttribute("aria-expanded","false")});
  function showCustom(){const custom=choice.value===SERVER_CUSTOM;server.hidden=!custom;serverLabel.hidden=!custom}
  async function refreshStatus(){
    status.textContent="Checking server and local Whisper…";
    const current=loadConfig(),device=localCapability();
    let serverText=current.serverUrl?"Server check pending":"Server URL not configured";
    if(current.rejectedServer)serverText="Invalid server URL (HTTPS required)";
    else if(current.serverUrl){const health=await serverHealthy(current.serverUrl);serverText=health.ok?"Sanket server: ONLINE":"Sanket server: NOT AVAILABLE — "+health.reason}
    const localText=device.ok?"Local Whisper: available ("+(device.webgpu?"WebGPU":"WASM")+")":"Local Whisper: unavailable";
    status.textContent=serverText+"\n"+localText+"\nDefault: "+(current.mode==="auto"?"server first, local fallback":current.mode==="server"?"server only":"local only")+"\nDestination: "+current.targetLanguage+" (local model; server may ignore destination language).";
  }
  function persist(){
    showCustom();const custom=choice.value===SERVER_CUSTOM,typed=server.value.trim();
    if(custom&&typed&&!isAllowedServer(typed)){status.textContent="Custom URL must start with HTTPS. Not saved.";return}
    saveConfig({mode:mode.value,serverChoice:custom?SERVER_CUSTOM:SERVER_SANKET,serverUrl:custom?typed:SANKET_TRANSCRIBE_SERVER,language:language.value,translate:translate.checked,targetLanguage:target.value});
    refreshStatus();
  }
  [mode,choice,server,language,translate,target].forEach(el=>el.addEventListener("change",persist));
  $("#ptt2RunCheck").addEventListener("click",refreshStatus);
  showCustom();refreshStatus();
}
