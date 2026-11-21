# Sanket link book

All PTT and app URLs are built in this folder. Pages put `data-link="key"` on an anchor or iframe. `apply.js` fills `href` or `src` from `links.js`. The static `href`/`src` already points at `https://sanketptt.com` so the control still works with JavaScript off.

`links.json` is the same table in data form. Change `links.js`, then refresh the JSON (the link check compares them).

## How to change a link

1. Edit the path in `links.js` (`url("radio/")`, a channel id, or a `source` entry).
2. Run `bash scripts/check-links.sh`. It rewrites nothing; it fails if `links.json` does not match.
3. Regenerate the JSON from the module if the check says it is out of date:

```bash
node --input-type=module -e 'import {writeFileSync} from "node:fs"; import {BASE,channels,links,roles} from "./website/ptt/links.js"; const out={base:BASE,channels,sanitizer:"letters, numbers, hyphens; max 40", links:Object.fromEntries(Object.entries(links).map(([k,href])=>([k,{href,role:roles[k]}])))}; writeFileSync("website/ptt/links.json", JSON.stringify(out,null,2)+"\n");'
```

Preview deploys rewrite the site origin inside this module to `/preview`. Pass paths to `url()` without a leading slash so that rewrite does not prefix them a second time. Do not hard-code `/preview` here.

## Guards

`scripts/check-links.sh` runs in the Hostinger deploy. It fails the job when any file under `website/` contains the GitHub Pages hostname (`github` + `.io`) or the raw file host (`raw.` + `githubusercontent.com`). The only exception is a line in `links.js` or `links.json` marked `source-entry`. Source entries are `github.com` repository links, not Pages links.

`rewriteLegacy()` in `links.js` runs on every URL this module returns. A Pages URL for this project is mapped onto `https://sanketptt.com`: the old site root becomes `/radio/`, `website/` is removed, and the Boondock Pages radio becomes `/boondock/`. The Pages hostname is assembled in pieces so the check above still sees a real leak.

## Keys

| Key | URL | Role | Used by |
|---|---|---|---|
| `home` | `/` | app | DMR “Main Website” |
| `ptt` | `/radio/` | app | Header OPEN PTT, product card, dashboard, Launch Sanket PTT, radio hub “Open PTT” |
| `pttVirtual` | `/radio/?ch=virtual` | app | Start free, DMR “Main PTT” |
| `pttEmbed` | `/radio/?ch=virtual&embed=1` | app | Homepage PTT iframe |
| `channel` + `data-channel` | `/radio/?ch=<id>` | builder | Radio hub channel buttons and custom channel |
| `embed` + `data-channel` | `/radio/?ch=<id>&embed=1` | builder | demo.html PTT iframe |
| `channelVirtual` | `/radio/?ch=virtual` | app | Radio hub Virtual |
| `channelMaster` | `/radio/?ch=master` | app | Radio hub Master |
| `channelCityControl` | `/radio/?ch=city-control` | app | Radio hub City Control |
| `channelKolkataControl` | `/radio/?ch=kolkata-control` | app | Radio hub Kolkata Control |
| `channelWebsiteDemo` | `/radio/?ch=sanket-website-demo` | app | Demo channel |
| `embedWebsiteDemo` | `/radio/?ch=sanket-website-demo&embed=1` | app | Demo embed |
| `transcribe` | `/transcribe/` | app | Transcribe buttons |
| `transcribeCompact` | `/transcribe/?compact=1&ch=virtual` | app | Homepage transcription iframe |
| `transcribeFor` + `data-channel` | `/transcribe/?ch=<id>` | builder | Radio and dev “Open Transcribe” |
| `transcribeDemo` | `/transcribe/?demo=1&autostart=1&compact=1&ch=<id>` | builder | demo.html transcription iframe |
| `dmr` | `/dmr/` | app | Header DMR, radio hub |
| `aakashvani` | `/aakashvani/` | app | Pricing card, homepage iframe, radio hub |
| `demo` | `/demo.html` | app | Radio hub demo card |
| `radioHub` | `/radio-hub.html` | app | Reserved for hub links |
| `try` | `/try/` | app | Try it page and the homepage Try it link |
| `dev` | `/dev/` | app | Radio hub development card. The repo `dev/` app is copied to `website/dev/` and the deploy publishes that folder. |
| `boondock` | `/boondock/radio/` | app | Radio hub Boondock card. The radio and its transcribe page are copied under `website/boondock/`. |
| `brandmeister` | BrandMeister | external | DMR page |
| `hoseline` | Hoseline | external | DMR page |
| `sourceSanketptt` | repository source entry | source | Radio hub |
| `sourceSanketpttDev` | tree `dev` | source | Radio hub |
| `sourceSanketpttDmr` | tree `dmr` | source | Radio hub |
| `sourceSanketpttAakashvani` | tree `aakashvani` | source | Radio hub |
| `sourceSanketpttTranscribe` | tree `transcribe` | source | Radio hub |
| `sourceDemo` | blob `website/demo.html` | source | Radio hub |
| `sourceSanketpttAudit` | audit branch | source | Radio hub |
| `sourceBoondock` | boondock-echo-live | source | Radio hub |
| `sourceBoondockAudit` | boondock audit branch | source | Radio hub |
| `sourcePttRadio` | ptt-radio | source | Radio hub |
| `sourcePttRadioAudit` | ptt-radio audit branch | source | Radio hub |
| `sourceStoryRadio` | sanket-story-radio | source | Radio hub |
| `sourceChitrakoot` | chitrakoot-sanket-radio | source | Radio hub |
| `sourceHyderabad` | hyderabad-police-ptt | source | Radio hub |
| `sourceHyderabadAudit` | hyderabad audit branch | source | Radio hub |
| `sourceAkashvaniStations` | codito/akashvani | source | Station list provenance. The playable list itself is `website/data/radio-directory.json`. |

## PTT to transcribe

All of these radios publish on MQTT prefix `ptt-radio-66ab9178/` plus the channel id, then `audio`, `floor`, and `presence`. Sanket Transcribe subscribes to that same prefix when opened with `?ch=` and `compact=1`. An explicit `ch` on the transcribe URL wins over a channel saved in the browser.

| PTT | Channel | Topic | Transcribe | Status |
|---|---|---|---|---|
| `/radio/` | `virtual` | `ptt-radio-66ab9178/virtual/audio` | `/transcribe/?compact=1&ch=virtual` | existing |
| `/radio/` | `master` | `ptt-radio-66ab9178/master/audio` | `/transcribe/?compact=1&ch=master` | existing |
| `/radio/` | `city-control` | `ptt-radio-66ab9178/city-control/audio` | `/transcribe/?compact=1&ch=city-control` | existing |
| `/radio/` | `kolkata-control` | `ptt-radio-66ab9178/kolkata-control/audio` | `/transcribe/?compact=1&ch=kolkata-control` | existing |
| `/radio/` | `sanket-website-demo` | `ptt-radio-66ab9178/sanket-website-demo/audio` | `/transcribe/?compact=1&ch=sanket-website-demo` | existing |
| `/dev/` | `dev` on the Try page (default with no `ch` is `virtual`) | `ptt-radio-66ab9178/dev/audio` | `/transcribe/?compact=1&ch=dev` | built |
| `/boondock/radio/` | `boondock` on the Try page (default with no `ch` is `virtual`) | `ptt-radio-66ab9178/boondock/audio` | `/transcribe/?compact=1&ch=boondock` | built |
| `/dmr/` | BrandMeister talkgroups, not a Sanket channel | none | none | no transcriber |
| `/aakashvani/` | venue preview, no relay | none | none | no transcriber |

`pairEmbed`, `pairListen`, and `pairOpen` in `links.js` build the Try page URLs. Do not paste those URLs into the page.

Channel ids: `virtual`, `master`, `city-control`, `kolkata-control`, `sanket-website-demo`, `dev`, `boondock`.

`sanitizeChannel()` keeps letters, numbers, and hyphens, and stops at 40 characters. Build a channel with `channelUrl(id)` or `embedUrl(id)`. Do not write a character class in a page.
