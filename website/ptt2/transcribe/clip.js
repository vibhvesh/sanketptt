/** Inspect a radio WAV before it is sent. The recorder writes 16-bit mono PCM at 12 kHz. */

export const MIN_SECONDS = 0.8;
/** Full-scale RMS below this is treated as silence. 500 is about -36 dBFS. */
export const MIN_RMS = 500;

function textAt(view, offset, length) {
  let out = "";
  for (let i = 0; i < length; i++) out += String.fromCharCode(view.getUint8(offset + i));
  return out;
}

/** PCM starts at the data chunk, which is not always byte 44. */
export function readPcm(wavBuffer) {
  const bytes = wavBuffer && wavBuffer.byteLength ? wavBuffer.byteLength : 0;
  if (bytes < 44) return null;
  const view = new DataView(wavBuffer);
  if (textAt(view, 0, 4) !== "RIFF" || textAt(view, 8, 4) !== "WAVE") return null;
  let rate = 0;
  let dataStart = 0;
  let dataBytes = 0;
  let offset = 12;
  while (offset + 8 <= bytes) {
    const id = textAt(view, offset, 4);
    const size = view.getUint32(offset + 4, true);
    const body = offset + 8;
    if (id === "fmt " && size >= 16 && body + 16 <= bytes) rate = view.getUint32(body + 4, true);
    if (id === "data") {
      dataStart = body;
      dataBytes = size;
      break;
    }
    if (size < 0) return null;
    offset = body + size + (size & 1);
  }
  if (!rate || rate < 8000 || rate > 48000) return null;
  if (dataBytes < 2 || (dataBytes & 1) || dataStart + dataBytes > bytes) return null;
  return {
    rate,
    pcm: new Int16Array(wavBuffer, dataStart, dataBytes >> 1),
  };
}

export function inspectWav(wavBuffer) {
  const parsed = readPcm(wavBuffer);
  if (!parsed) return { ok: false, reason: "incomplete" };
  const { rate, pcm } = parsed;
  const duration = pcm.length / rate;
  let sum = 0;
  for (let i = 0; i < pcm.length; i++) sum += pcm[i] * pcm[i];
  const rms = Math.sqrt(sum / pcm.length);
  if (duration < MIN_SECONDS || rms < MIN_RMS) {
    return { ok: false, reason: "too short", duration, rms, rate };
  }
  return { ok: true, duration, rms, rate, samples: pcm.length };
}
