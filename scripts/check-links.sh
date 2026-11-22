#!/usr/bin/env bash
# Fail when first-party website code still points at GitHub Pages or raw GitHub
# file hosts. The public radio catalogue is intentionally exempt: it preserves
# third-party station homepage and favicon URLs supplied by its directory source.
# A line in website/ptt/links.js or links.json may carry those hosts only when
# it is marked source-entry. The runtime guard builds the Pages hostname from
# pieces, so the guard itself does not trip this check.
set -euo pipefail
cd "$(dirname "$0")/.."

pattern='github\\.io|raw\\.githubusercontent\\.com'
fail=0
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  file="${line%%:*}"
  # These are third-party catalogue metadata, not Sanket application links.
  if [[ "$file" == website/data/radio-directory.json ]]; then
    continue
  fi
  if [[ "$file" == website/ptt/links.js || "$file" == website/ptt/links.json ]] && [[ "$line" == *source-entry* ]]; then
    continue
  fi
  echo "Forbidden GitHub host: $line"
  fail=1
done < <(grep -RInI -E "$pattern" website || true)

if [[ "$fail" -ne 0 ]]; then
  echo "Link check failed. Remove GitHub-hosted links from first-party site code or self-host the asset."
  exit 1
fi

node --input-type=module << 'JS'
import { readFileSync } from "node:fs";
import {
  BASE, sanitizeChannel, channelUrl, embedUrl, transcribeDemo, rewriteLegacy, links, roles,
} from "./website/ptt/links.js";

const expect = [
  [sanitizeChannel("sanket-website-demo"), "sanket-website-demo"],
  [sanitizeChannel("Unit Alpha!"), "UnitAlpha"],
  [channelUrl("sanket-website-demo"), BASE + "/radio/?ch=sanket-website-demo"],
  [embedUrl("virtual"), BASE + "/radio/?ch=virtual&embed=1"],
  [transcribeDemo("sanket-website-demo"), BASE + "/transcribe/?demo=1&autostart=1&compact=1&ch=sanket-website-demo"],
  [rewriteLegacy("https://vibhvesh." + ["github", "io"].join(".") + "/sanketptt/?ch=virtual&embed=1"), BASE + "/radio/?ch=virtual&embed=1"],
  [rewriteLegacy("https://vibhvesh." + ["github", "io"].join(".") + "/sanketptt/website/demo.html"), BASE + "/demo.html"],
  [rewriteLegacy("https://vibhvesh." + ["github", "io"].join(".") + "/sanketptt/transcribe/?compact=1"), BASE + "/transcribe/?compact=1"],
  [rewriteLegacy("https://vibhvesh." + ["github", "io"].join(".") + "/boondock-echo-live/radio/"), BASE + "/boondock/radio/"],
  [links.ptt, BASE + "/radio/"],
  [links.dev, BASE + "/dev/"],
  [links.boondock, BASE + "/boondock/radio/"],
];
for (const [got, want] of expect) {
  if (got !== want) {
    console.error("link module mismatch\\n got:  " + got + "\\n want: " + want);
    process.exit(1);
  }
}
if (roles.sourceSanketptt !== "source" || !links.sourceSanketptt.includes("github.com/")) {
  console.error("source entries must stay labelled and point at github.com");
  process.exit(1);
}
const book = JSON.parse(readFileSync("website/ptt/links.json", "utf8"));
for (const [key, href] of Object.entries(links)) {
  const row = book.links[key];
  if (!row || row.href !== href || row.role !== roles[key]) {
    console.error("links.json out of date for " + key);
    process.exit(1);
  }
}
JSON.parse(readFileSync("website/data/radio-directory.json", "utf8"));
console.log("link module ok (" + Object.keys(links).length + " keys); radio catalogue JSON valid");
JS

echo "No GitHub-hosted links in first-party website code."
