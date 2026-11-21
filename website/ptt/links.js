/**
 * Sanket PTT link book.
 * Every app, channel, embed, and source URL is built here.
 * Pages ask for a key. They do not assemble these URLs themselves.
 *
 * BASE is the public site origin. The preview deploy rewrites this
 * string to /preview so the same module serves the preview tree.
 */
export const BASE = "https://sanketptt.com";

/** Channel ids used by the homepage, demo, and radio hub. */
export const channels = Object.freeze({
  virtual: "virtual",
  master: "master",
  cityControl: "city-control",
  kolkataControl: "kolkata-control",
  websiteDemo: "sanket-website-demo",
});

const PAGES_HOST = ["github", "io"].join(".");

function origin() {
  return String(BASE).replace(/\/+$/, "");
}

/**
 * Keep letters, numbers, and hyphens. This is the only channel sanitizer.
 * A doubled backslash in front of "w" used to turn sanket-website-demo into -w-.
 */
export function sanitizeChannel(value) {
  return String(value ?? "")
    .trim()
    .replace(/[^A-Za-z0-9-]/g, "")
    .slice(0, 40);
}

/**
 * Send a legacy GitHub Pages Sanket or Boondock URL to the copy hosted here.
 * Other URLs, including github.com source links, are returned unchanged.
 */
export function rewriteLegacy(input) {
  const raw = String(input ?? "").trim();
  let parsed;
  try {
    parsed = new URL(raw);
  } catch (e) {
    return raw;
  }
  const host = parsed.hostname.toLowerCase();
  if (host !== PAGES_HOST && !host.endsWith("." + PAGES_HOST)) return raw;
  const path = parsed.pathname.replace(/^\/+/, "");
  const tail = parsed.search + parsed.hash;
  if (path === "boondock-echo-live" || path.startsWith("boondock-echo-live/")) {
    const rest = path.slice("boondock-echo-live/".length).replace(/^\/+/, "");
    return origin() + "/" + "boondock/" + rest + tail;
  }
  if (path === "sanketptt" || path.startsWith("sanketptt/")) {
    let rest = path.slice("sanketptt/".length).replace(/^\/+/, "");
    if (rest.startsWith("website/")) rest = rest.slice("website/".length);
    if (rest === "" || rest === "index.html") return origin() + "/" + "radio/" + tail;
    return origin() + "/" + rest + tail;
  }
  return raw;
}

/**
 * Build an absolute URL on this site, then pass it through the legacy guard.
 * Pass the path without a leading slash. The preview deploy prefixes quoted
 * slash-paths such as a leading slash plus radio/, and this function adds that slash.
 */
export function url(path, query) {
  const clean = "/" + String(path || "").replace(/^\/+/, "");
  let out = origin() + clean;
  if (query) {
    const q = String(query).replace(/^\?/, "");
    if (q) out += (out.includes("?") ? "&" : "?") + q;
  }
  return rewriteLegacy(out);
}

export function channelUrl(id) {
  const ch = sanitizeChannel(id);
  return ch ? url("radio/", "ch=" + encodeURIComponent(ch)) : url("radio/");
}

export function embedUrl(id) {
  const ch = sanitizeChannel(id) || channels.virtual;
  return url("radio/", "ch=" + encodeURIComponent(ch) + "&embed=1");
}

export function transcribeFor(id) {
  const ch = sanitizeChannel(id);
  return ch ? url("transcribe/", "ch=" + encodeURIComponent(ch)) : url("transcribe/");
}

export function transcribeCompact(id) {
  const ch = sanitizeChannel(id) || channels.virtual;
  return url("transcribe/", "compact=1&ch=" + encodeURIComponent(ch));
}

export function transcribeDemo(id) {
  const ch = sanitizeChannel(id) || channels.websiteDemo;
  return url("transcribe/", "demo=1&autostart=1&compact=1&ch=" + encodeURIComponent(ch));
}

/** github.com repository links. Marked source-entry so the link check can see the label. */
export const source = Object.freeze({
  sanketptt: "https://github.com/vibhvesh/sanketptt", // source-entry
  sanketpttDev: "https://github.com/vibhvesh/sanketptt/tree/main/dev", // source-entry
  sanketpttDmr: "https://github.com/vibhvesh/sanketptt/tree/main/dmr", // source-entry
  sanketpttAakashvani: "https://github.com/vibhvesh/sanketptt/tree/main/aakashvani", // source-entry
  sanketpttTranscribe: "https://github.com/vibhvesh/sanketptt/tree/main/transcribe", // source-entry
  demo: "https://github.com/vibhvesh/sanketptt/blob/main/website/demo.html", // source-entry
  sanketpttAudit: "https://github.com/vibhvesh/sanketptt/tree/audit/radio-stability-2026-11-19", // source-entry
  boondock: "https://github.com/vibhvesh/boondock-echo-live", // source-entry
  boondockAudit: "https://github.com/vibhvesh/boondock-echo-live/tree/audit/radio-stability-2026-11-19", // source-entry
  pttRadio: "https://github.com/vibhvesh/ptt-radio", // source-entry
  pttRadioAudit: "https://github.com/vibhvesh/ptt-radio/tree/audit/radio-stability-2026-11-19", // source-entry
  storyRadio: "https://github.com/vibhvesh/sanket-story-radio", // source-entry
  chitrakoot: "https://github.com/vibhvesh/chitrakoot-sanket-radio", // source-entry
  hyderabad: "https://github.com/vibhvesh/hyderabad-police-ptt", // source-entry
  hyderabadAudit: "https://github.com/vibhvesh/hyderabad-police-ptt/tree/audit/radio-stability-2026-11-19", // source-entry
  akashvaniStations: "https://github.com/codito/akashvani", // source-entry
});

export const links = Object.freeze({
  home: url(""),
  ptt: url("radio/"),
  pttVirtual: channelUrl(channels.virtual),
  pttEmbed: embedUrl(channels.virtual),
  channelVirtual: channelUrl(channels.virtual),
  channelMaster: channelUrl(channels.master),
  channelCityControl: channelUrl(channels.cityControl),
  channelKolkataControl: channelUrl(channels.kolkataControl),
  channelWebsiteDemo: channelUrl(channels.websiteDemo),
  embedWebsiteDemo: embedUrl(channels.websiteDemo),
  transcribe: url("transcribe/"),
  transcribeCompact: transcribeCompact(channels.virtual),
  transcribeDemo: transcribeDemo(channels.websiteDemo),
  dmr: url("dmr/"),
  aakashvani: url("aakashvani/"),
  demo: url("demo.html"),
  radioHub: url("radio-hub.html"),
  dev: url("dev/"),
  boondock: url("boondock/radio/"),
  brandmeister: "https://brandmeister.network/",
  hoseline: "https://hose.brandmeister.network/",
  sourceSanketptt: source.sanketptt,
  sourceSanketpttDev: source.sanketpttDev,
  sourceSanketpttDmr: source.sanketpttDmr,
  sourceSanketpttAakashvani: source.sanketpttAakashvani,
  sourceSanketpttTranscribe: source.sanketpttTranscribe,
  sourceDemo: source.demo,
  sourceSanketpttAudit: source.sanketpttAudit,
  sourceBoondock: source.boondock,
  sourceBoondockAudit: source.boondockAudit,
  sourcePttRadio: source.pttRadio,
  sourcePttRadioAudit: source.pttRadioAudit,
  sourceStoryRadio: source.storyRadio,
  sourceChitrakoot: source.chitrakoot,
  sourceHyderabad: source.hyderabad,
  sourceHyderabadAudit: source.hyderabadAudit,
  sourceAkashvaniStations: source.akashvaniStations,
});

export const roles = Object.freeze({
  home: "app",
  ptt: "app",
  pttVirtual: "app",
  pttEmbed: "app",
  channelVirtual: "app",
  channelMaster: "app",
  channelCityControl: "app",
  channelKolkataControl: "app",
  channelWebsiteDemo: "app",
  embedWebsiteDemo: "app",
  transcribe: "app",
  transcribeCompact: "app",
  transcribeDemo: "app",
  dmr: "app",
  aakashvani: "app",
  demo: "app",
  radioHub: "app",
  dev: "app",
  boondock: "app",
  brandmeister: "external",
  hoseline: "external",
  sourceSanketptt: "source",
  sourceSanketpttDev: "source",
  sourceSanketpttDmr: "source",
  sourceSanketpttAakashvani: "source",
  sourceSanketpttTranscribe: "source",
  sourceDemo: "source",
  sourceSanketpttAudit: "source",
  sourceBoondock: "source",
  sourceBoondockAudit: "source",
  sourcePttRadio: "source",
  sourcePttRadioAudit: "source",
  sourceStoryRadio: "source",
  sourceChitrakoot: "source",
  sourceHyderabad: "source",
  sourceHyderabadAudit: "source",
  sourceAkashvaniStations: "source",
});
