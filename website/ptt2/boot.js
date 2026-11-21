import { mountSettings, watchRecorder } from "./transcribe/ui.js";

const settings = document.getElementById("ptt2Settings");
if (settings) mountSettings(settings);
if (typeof rec !== "undefined" && typeof renderLog === "function") {
  watchRecorder(rec, renderLog);
}
