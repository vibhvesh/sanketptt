/**
 * Fill [data-link="key"] from the link book.
 * Load this module on every page that shows a PTT or app link.
 */
import {
  links,
  rewriteLegacy,
  channelUrl,
  embedUrl,
  transcribeFor,
  transcribeCompact,
  transcribeDemo,
  sanitizeChannel,
  url,
  BASE,
  channels,
  source,
  roles,
} from "./links.js";

const builders = {
  channel: (el) => channelUrl(el.getAttribute("data-channel") || "virtual"),
  embed: (el) => embedUrl(el.getAttribute("data-channel") || "virtual"),
  transcribeFor: (el) => transcribeFor(el.getAttribute("data-channel") || ""),
  transcribeCompact: (el) => transcribeCompact(el.getAttribute("data-channel") || "virtual"),
  transcribeDemo: (el) => transcribeDemo(el.getAttribute("data-channel") || "sanket-website-demo"),
};

export function resolveLink(el) {
  const key = el.getAttribute("data-link");
  if (!key) return;
  const built = builders[key] ? builders[key](el) : links[key];
  if (!built) return;
  const attr = el.getAttribute("data-link-attr") || (el.tagName === "IFRAME" ? "src" : "href");
  el.setAttribute(attr, rewriteLegacy(built));
}

export function apply(root) {
  (root || document).querySelectorAll("[data-link]").forEach(resolveLink);
}

const api = {
  BASE,
  channels,
  source,
  roles,
  links,
  sanitizeChannel,
  rewriteLegacy,
  url,
  channelUrl,
  embedUrl,
  transcribeFor,
  transcribeCompact,
  transcribeDemo,
  apply,
  resolveLink,
};

window.SanketLinks = api;
apply(document);
document.dispatchEvent(new Event("sanket-links-ready"));
