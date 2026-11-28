/**
 * On-device transcription. The Whisper model is downloaded only when a clip needs it.
 * English tiny model: small enough to run in the browser over WASM, with WebGPU when present.
 */
import { readPcm } from "./clip.js";

const MODEL_ID = "onnx-community/whisper-tiny";
const LANGUAGE_NAMES = { en: "english", hi: "hindi" };
let pipelinePromise = null;
let translationPipelinePromise = null;
const NLLB_CODES = { en: "eng_Latn", hi: "hin_Deva", gu: "guj_Gujr", mr: "mar_Deva", bn: "ben_Beng", pa: "pan_Guru", ta: "tam_Taml", te: "tel_Telu", ur: "urd_Arab", zh: "zho_Hans", ru: "rus_Cyrl" };

function resampleTo16k(wavBuffer) {
  const parsed = readPcm(wavBuffer);
  if (!parsed) throw new Error("incomplete audio");
  const rate = parsed.rate;
  const data = parsed.pcm;
  const target = 16000;
  const outLen = Math.max(1, Math.floor(data.length * target / rate));
  const out = new Float32Array(outLen);
  for (let i = 0; i < outLen; i++) {
    const src = i * rate / target;
    const i0 = Math.floor(src);
    const frac = src - i0;
    const a = data[Math.min(i0, data.length - 1)] || 0;
    const b = data[Math.min(i0 + 1, data.length - 1)] || a;
    out[i] = (a * (1 - frac) + b * frac) / 32768;
  }
  return out;
}

async function chooseDevice() {
  if (!navigator.gpu || !navigator.gpu.requestAdapter) return "wasm";
  try {
    const adapter = await Promise.race([
      navigator.gpu.requestAdapter(),
      new Promise((resolve) => setTimeout(() => resolve(null), 1500)),
    ]);
    if (adapter) return "webgpu";
  } catch (e) {
    return "wasm";
  }
  return "wasm";
}

async function pipeline() {
  if (!pipelinePromise) {
    pipelinePromise = (async () => {
      const mod = await import("https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.7.6");
      mod.env.allowLocalModels = false;
      mod.env.useBrowserCache = true;
      const device = await chooseDevice();
      try {
        return await mod.pipeline("automatic-speech-recognition", MODEL_ID, { device, dtype: "q8" });
      } catch (e) {
        return mod.pipeline("automatic-speech-recognition", MODEL_ID, { device: "wasm" });
      }
    })();
  }
  return pipelinePromise;
}

export async function transcribeLocal(wavBuffer, config) {
  const audio = resampleTo16k(wavBuffer);
  const transcriber = await pipeline();
  const task = config && config.translate && (!config.targetLanguage || config.targetLanguage === "en") ? "translate" : "transcribe";
  const language = (config && config.language) || "en";
  const result = await transcriber(audio, {
    language: language === "auto" ? undefined : (LANGUAGE_NAMES[language] || language),
    task,
    return_timestamps: true,
  });
  const text = String(result && result.text || "").trim();
  const segments = Array.isArray(result && result.chunks) ? result.chunks.map((chunk) => ({
    text: String(chunk.text || "").trim(),
    start: chunk.timestamp ? chunk.timestamp[0] : null,
    end: chunk.timestamp ? chunk.timestamp[1] : null,
  })) : [];
  return { text, language, segments };
}

/** Optional multilingual on-device translation. First use downloads a large model and caches it. */
async function translationPipeline() {
  if (!translationPipelinePromise) {
    translationPipelinePromise = (async () => {
      const mod = await import("https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.7.6");
      mod.env.allowLocalModels = false;
      mod.env.useBrowserCache = true;
      const device = await chooseDevice();
      try {
        return await mod.pipeline("translation", "Xenova/nllb-200-distilled-600M", { device, dtype: "q8" });
      } catch (e) {
        return mod.pipeline("translation", "Xenova/nllb-200-distilled-600M", { device: "wasm" });
      }
    })();
  }
  return translationPipelinePromise;
}

export async function translateLocal(text, sourceLanguage, targetLanguage) {
  const target = NLLB_CODES[targetLanguage];
  if (!target) throw new Error("Local translation does not support this destination language yet.");
  const source = NLLB_CODES[sourceLanguage] || "eng_Latn";
  if (!String(text || "").trim()) return "";
  const translator = await translationPipeline();
  const result = await translator(String(text), { src_lang: source, tgt_lang: target, max_new_tokens: 256 });
  return String(result && result[0] && result[0].translation_text || "").trim();
}
