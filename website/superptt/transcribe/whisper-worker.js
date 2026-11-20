// Local Whisper (multilingual) in a module worker via transformers.js. Audio in: Float32 16 kHz.
import { pipeline, env } from 'https://cdn.jsdelivr.net/npm/@huggingface/transformers@3.7.1';
env.allowLocalModels = false;
let asr = null, cur = '';
async function load(model) {
  if (asr && cur === model) return asr;
  let dev = 'wasm';
  try { if (navigator.gpu && await navigator.gpu.requestAdapter()) dev = 'webgpu'; } catch (e) {}
  const opt = { progress_callback: p => self.postMessage({ t: 'progress', p }) };
  try { asr = await pipeline('automatic-speech-recognition', model, { ...opt, device: dev, dtype: dev === 'webgpu' ? 'fp32' : 'q8' }); }
  catch (e) { asr = await pipeline('automatic-speech-recognition', model, { ...opt, device: 'wasm', dtype: 'q8' }); }
  cur = model; self.postMessage({ t: 'ready', model }); return asr;
}
self.onmessage = async (e) => {
  const m = e.data;
  try {
    if (m.t === 'load') { await load(m.model); return; }
    const a = await load(m.model);
    const o = { task: 'transcribe', chunk_length_s: 30, stride_length_s: 5 };
    if (m.lang && m.lang !== 'auto') o.language = m.lang;
    const r = await a(m.audio, o);
    self.postMessage({ t: 'result', id: m.id, text: (r.text || '').trim() });
  } catch (err) { self.postMessage({ t: 'error', id: m.id, error: String(err && err.message || err) }); }
};
