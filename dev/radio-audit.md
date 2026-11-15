# Sanket PTT Dev — International Radio Stream Audit

Last updated: 2026-11-16 00:31 IST

## Status key

- **GREEN** — direct stream decoded and playback time advanced in a real browser test.
- **YELLOW** — candidate is reputable, but playback, CORS, format, geographic access, or continuous schedule is not yet verified.
- **RED** — repeatedly confirmed dead/invalid endpoint. A single timeout or a blocked test environment is never enough to mark RED.

## Current verified list

No GREEN streams yet. No RED streams yet.

## Candidate audit

| Station | Country | Language | Direct stream URL | Official source / evidence | 24/7 evidence | Status |
|---|---|---|---|---|---|---|
| BBC World Service | UK / international | English | https://stream.live.vc.bbcmedia.co.uk/bbc_world_service | BBC confirms free live World Service English access outside the UK via BBC.com and the BBC app: https://help.bbc.com/hc/en-us/articles/42652680528659-Update-on-access-to-BBC-Sounds-outside-the-UK. Direct CDN URL is listed by an external radio directory and still needs direct validation. | BBC guide lists World Service 24 hours on UK digital radio; verify online schedule and endpoint independently. | YELLOW |
| WNYC 93.9 FM | USA | English | https://fm939.wnyc.org/wnycfm | WNYC's own stream-format page lists this MP3 endpoint: https://prod.wnyc.org/audio-other-formats/. | Official site confirms live online service; full 24-hour schedule not independently checked. | YELLOW |
| WFMU Freeform | USA | English | https://stream0.wfmu.org/freeform-128k.mp3 | WFMU's own mobile/stream information page publishes this direct MP3 URL: https://freeform.wfmu.org/mobile.shtml. | Continuous station stream is offered; a formal 24-hour schedule statement was not confirmed in this run. | YELLOW |
| KCRW Eclectic24 | USA | English | https://kcrw.streamguys1.com/kcrw_192k_mp3_e24_internet_radio | KCRW describes Eclectic24 as its 24-hour music stream: https://www.kcrw.com/shows/eclectic24/latest. KCRW publishes a playlist link for Eclectic24 at https://newmedia.kcrw.com/legacy/pls/kcrwmusic.pls; the direct MP3 endpoint above is reported by third-party stream users and needs validation against the current playlist. | Official KCRW page explicitly says 24-hour all-music channel. | YELLOW |
| ABC NewsRadio | Australia | English | Not resolved — official live player only: https://www.abc.net.au/listen/live/news | ABC describes NewsRadio as a continuous national news network: https://www.abc.net.au/news/2021-11-16/newsradio-about-us/100623580. | ABC explicitly calls it continuous national news coverage. | YELLOW — no direct endpoint |

## Test log

### 2026-11-16 00:31 IST

- Fetched the current dev/index.html from vibhvesh/sanketptt (main).
- Found the scanner only used Hls.js. This meant MP3 streams such as BBC, WNYC and WFMU could never be positively verified by the old scanner.
- Updated the Dev player/scanner to distinguish HLS (.m3u8) from direct audio streams, use native audio playback for MP3/AAC, and mark GREEN only after the media element is actually playing and its playback clock advances. HLS candidates now also require playback-clock advancement rather than only a manifest/fragment event.
- Corrected the WNYC and WFMU direct MP3 URLs using their broadcaster-published stream information.
- Added KCRW Eclectic24 as an additional famous US public-radio candidate. It remains hidden from the selectable list unless the browser scanner verifies it.
- Attempted direct HTTP range tests against BBC, WNYC, WFMU, DW and RFI from the audit runner. All failed before connecting with DNS resolution error (Temporary failure in name resolution). Opening the media endpoints through the web reader also returned inaccessible-media errors. This is a runner/network limitation, not proof that the stations are down.
- Therefore no station was marked GREEN or RED in this run. All candidates remain YELLOW pending a real browser playback test.

## Removal policy

Do not delete any station from the selectable Dev source catalogue based on one failed check. Only consider removal after three consecutive hourly RED results with explicit HTTP 404/410 or equivalent confirmed invalid-source evidence. Preserve removed entries and their URLs in this file for restoration. CORS blocks, timeouts, geoblocking, unsupported browser formats, DNS failures in the audit runner, and inconclusive tests remain YELLOW.

## Implementation note

The Dev scanner now supports both HLS and direct MP3/AAC URLs. The station picker continues to show only GREEN stations. The browser's successful playback test is the authority for GREEN status; research evidence alone never upgrades a station to GREEN.
