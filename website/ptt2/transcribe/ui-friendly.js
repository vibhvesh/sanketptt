import { SANKET_TRANSCRIBE_SERVER, loadConfig } from "./config.js";
import { serverHealthy } from "./detect.js";
import { transcribeTransmission } from "./router.js";
import { lineFromRadio } from "./line.js";
const notes = new Map();

function escapeText(value) {
  return String(value).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
}

function lineHtml(note, key) {
  if (!note || note.pending) return '<div class="ptt2-transcript-state"><i></i>Transcribing...</div>';
  if (note.skipped) return '<div class="ptt2-transcript-state muted">Audio too short to transcribe</div>';
  if (note.failed) return '<div class="ptt2-transcript-state error"><span>We couldn’t transcribe this message. Please try again.</span><button type="button" class="ptt2-retry" aria-label="Retry transcription" data-retry="' + key + '">↻ Retry</button></div>';
  const text = note.text ? escapeText(note.text) : 'No speech detected';
  return '<div class="ptt2-transcript-box"><div class="ptt2-transcript-text">' + text + '</div></div>';
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
  root.hidden = true;
  root.innerHTML = `
    <div class="ptt2-settings-head"><h3>SERVER SETTINGS &amp; REPORT</h3><button type="button" id="ptt2SettingsClose" aria-label="Close settings">×</button></div>
    <p class="ptt2-hint">All audio transcription is performed by Sanket Transcribe. The server selects the speech model, language handling and translation policy. This client never runs local transcription.</p>
    <div class="ptt2-report"><b>SANKET TRANSCRIPTION SERVER</b><p id="ptt2Status">Checking server…</p><button type="button" id="ptt2RunCheck">Check server again</button></div>
  `;
  const status=root.querySelector("#ptt2Status");
  root.querySelector("#ptt2SettingsClose").addEventListener("click",()=>{
    root.hidden=true;
    const button=document.getElementById("ptt2SettingsToggle");
    if(button)button.setAttribute("aria-expanded","false");
  });
  async function refreshStatus(){
    status.textContent="Checking "+SANKET_TRANSCRIBE_SERVER+" …";
    const config=loadConfig();
    const health=await serverHealthy(config.serverUrl);
    status.textContent=health.ok
      ? "ONLINE · Sanket Transcribe is responding. Server-managed model selection is active. All transcription results come from this server."
      : "OFFLINE / ERROR · "+health.reason+" Transcription will report an error until the server is available. No local fallback will occur.";
  }
  root.querySelector("#ptt2RunCheck").addEventListener("click",refreshStatus);
  refreshStatus();
}
