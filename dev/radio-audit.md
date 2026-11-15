# Sanket PTT Dev — International Radio Stream Audit

Last updated: 2026-11-16 01:41 IST

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
| RTÉ Radio 1 | Ireland | English | https://www.rte.ie/manifests/radio1.m3u8 | RTÉ publishes this live HLS manifest for internet-radio devices: https://www.rte.ie/radio/radio1/static/2021/0704/1232947-rte-radio-help-support/. | Continuous stream is offered; formal 24-hour schedule not confirmed in this run. | YELLOW |
| RTÉ 2FM | Ireland | English | https://www.rte.ie/manifests/2fm.m3u8 | RTÉ publishes this live HLS manifest on its official support page above. | Formal 24-hour schedule not confirmed in this run. | YELLOW |
| RTÉ Raidió na Gaeltachta | Ireland | Irish | https://www.rte.ie/manifests/rnag.m3u8 | RTÉ publishes this live HLS manifest on its official support page above. | Formal 24-hour schedule not confirmed in this run. | YELLOW |

## Test log

### 2026-11-16 00:31 IST

- Fetched the current dev/index.html from vibhvesh/sanketptt (main).
- Found the scanner only used Hls.js. This meant MP3 streams such as BBC, WNYC and WFMU could never be positively verified by the old scanner.
- Updated the Dev player/scanner to distinguish HLS (.m3u8) from direct audio streams, use native audio playback for MP3/AAC, and mark GREEN only after the media element is actually playing and its playback clock advances. HLS candidates now also require playback-clock advancement rather than only a manifest/fragment event.
- Corrected the WNYC and WFMU direct MP3 URLs using their broadcaster-published stream information.
- Added KCRW Eclectic24 as an additional famous US public-radio candidate and RTÉ Radio 1, 2FM and Raidió na Gaeltachta using RTÉ-published HLS manifests. They remain hidden from the selectable list unless the browser scanner verifies them.
- Attempted direct HTTP range tests against BBC, WNYC, WFMU, DW and RFI from the audit runner. All failed before connecting with DNS resolution error (Temporary failure in name resolution). Opening the media endpoints through the web reader also returned inaccessible-media errors. This is a runner/network limitation, not proof that the stations are down.
- Therefore no station was marked GREEN or RED in this run. All candidates remain YELLOW pending a real browser playback test.

## Latest cumulative snapshot — 2026-11-16 01:41 IST

- **GREEN:** none — no candidate has passed a real audio decode/playback test from this audit runner.
- **YELLOW:** BBC World Service; WNYC 93.9; WFMU Freeform; KCRW Eclectic24; RTÉ Radio 1; RTÉ 2FM; RTÉ Raidió na Gaeltachta; ABC NewsRadio (official player only); WQXR 105.9; WNYC New Sounds.
- **RED:** none — no origin-server 404/410 or other repeatedly confirmed invalid response was obtained.
- Existing Indian station catalogue was left unchanged. Prasar Bharati's official livestream page lists its 17 core AIR live channels, and the Akashvani live-radio catalogue exposes a much wider regional station directory. These pages support the Indian station identities/languages, not a fresh playback test of every direct URL.

## Station-by-station update — 2026-11-16 01:41 IST

| Station | Country | Language | Candidate direct URL | Official source / latest evidence | Manifest / HTTP result | Audio-segment / playback result | Status |
|---|---|---|---|---|---|---|---|
| BBC World Service | UK / international | English | https://stream.live.vc.bbcmedia.co.uk/bbc_world_service | BBC says World Service English remains available internationally via BBC.com and the BBC app: https://help.bbc.com/hc/en-us/articles/42652680528659-Update-on-access-to-BBC-Sounds-outside-the-UK. The direct CDN URL is still sourced from radio-directory listings, not the BBC help page. | Direct endpoint could not be fetched by the audit runner; no origin HTTP status. | No audio bytes decoded; playback not verified. | YELLOW |
| WNYC 93.9 FM | USA | English | https://fm939.wnyc.org/wnycfm | WNYC's official page explicitly publishes this MP3 64 kbps URL and an AAC alternative https://fm939.wnyc.org/wnycfm.aac: https://prod.wnyc.org/audio-other-formats/. | Direct endpoint could not be fetched by the audit runner; no origin HTTP status. | No MP3/AAC bytes decoded; playback not verified. | YELLOW |
| WFMU Freeform | USA | English | Dev candidate: https://stream0.wfmu.org/freeform-128k.mp3 | WFMU's official mobile page lists 128k and 32k MP3 streams at http://stream0.wfmu.org/freeform-128k.mp3 and http://stream0.wfmu.org/freeform-32k.mp3: https://freeform.wfmu.org/mobile.shtml. The HTTPS variant currently in Dev has not been independently validated. | DNS lookup failed before any origin HTTP response. | No MP3 bytes decoded; playback not verified. | YELLOW |
| KCRW Eclectic24 | USA | English | https://kcrw.streamguys1.com/kcrw_192k_mp3_e24_internet_radio | KCRW's official page describes Eclectic24 as a 24-hour all-music channel: https://www.kcrw.com/shows/eclectic24/latest. The candidate direct endpoint is not published on that page and remains third-party sourced. | Direct endpoint could not be fetched by the audit runner; no origin HTTP status. | No MP3 bytes decoded; playback not verified. | YELLOW |
| RTÉ Radio 1 | Ireland | English | https://www.rte.ie/manifests/radio1.m3u8 | RTÉ's official support article lists this HLS manifest and the corresponding .m3u: https://www.rte.ie/radio/radio1/static/2021/0704/1232947-rte-radio-help-support/. RTÉ announced the old Radio Player will stop working on 16 Nov 2026 and is being replaced by RTÉ Listen: https://www.rte.ie/radio/support/2026/0728/1585419-rte-listen-support/. Treat the older manifest as potentially stale until revalidated. | Web reader returned 403 for the manifest URL; this is a proxy/tool response, not a verified origin response. | No media segment fetched or decoded; playback not verified. | YELLOW |
| RTÉ 2FM | Ireland | English | https://www.rte.ie/manifests/2fm.m3u8 | RTÉ's official support article lists this HLS manifest: https://www.rte.ie/radio/radio1/static/2021/0704/1232947-rte-radio-help-support/. RTÉ Listen transition dated 16 Nov 2026 may affect legacy player URLs: https://www.rte.ie/radio/support/2026/0728/1585419-rte-listen-support/. | Web reader returned 403 for the manifest URL; origin reachability is unknown. | No media segment fetched or decoded; playback not verified. | YELLOW |
| RTÉ Raidió na Gaeltachta | Ireland | Irish | https://www.rte.ie/manifests/rnag.m3u8 | RTÉ's official support article lists this HLS manifest: https://www.rte.ie/radio/radio1/static/2021/0704/1232947-rte-radio-help-support/. RTÉ Listen transition dated 16 Nov 2026 may affect legacy player URLs: https://www.rte.ie/radio/support/2026/0728/1585419-rte-listen-support/. | Web reader returned 403 for the manifest URL; origin reachability is unknown. | No media segment fetched or decoded; playback not verified. | YELLOW |
| ABC NewsRadio | Australia | English | Not resolved — official live player only: https://www.abc.net.au/listen/live/news | ABC describes ABC NEWS on radio as a national 24-hour radio news network: https://www.abc.net.au/about/abc-services/103700030. ABC's 2026 stream-distribution update recommends ABC listen for direct listening and notes changes to third-party streams: https://help.abc.net.au/hc/en-us/articles/15071793950607-Changes-to-ABC-Radio-Live-Streams-on-Third-Party-Platforms. | No direct stream endpoint available to test. | No direct stream playback test possible. | YELLOW |
| WQXR 105.9 FM | USA | English | https://stream.wqxr.org/wqxr | WNYC / New York Public Radio's official formats page publishes this MP3 128 kbps stream and AAC alternative https://stream.wqxr.org/wqxr.aac: https://prod.wnyc.org/audio-other-formats/. New discovery candidate; not yet added to Dev. | Direct endpoint could not be fetched by the audit runner; no origin HTTP status. | No MP3/AAC bytes decoded; playback not verified. | YELLOW |
| WNYC New Sounds | USA | English | https://q2stream.wqxr.org/q2 | WNYC's official formats page publishes this MP3 128 kbps stream and AAC alternative https://q2stream.wqxr.org/q2.aac: https://prod.wnyc.org/audio-other-formats/. New discovery candidate; not yet added to Dev. | Direct endpoint could not be fetched by the audit runner; no origin HTTP status. | No MP3/AAC bytes decoded; playback not verified. | YELLOW |

### Test log — 2026-11-16 01:41 IST

- Re-fetched the current Dev source and audit record from GitHub. The seven international endpoints already in Dev are unchanged.
- Re-tested all seven Dev international candidate URLs from the audit runner with HTTP Range requests (bytes 0–4095), a 5-second connection timeout and a 12-second overall timeout. Every attempt failed at DNS resolution ("Could not resolve host") before connecting. No HTTP status, manifest body, MP3/AAC frames or HLS media segments were received.
- Attempted direct endpoint opens through the web reader. BBC, WNYC, WFMU and KCRW media endpoints were inaccessible to that reader; RTÉ's manifest URL returned a reader-side 403. These are tool/proxy limitations and are not origin-server 404/410 evidence.
- Independently fetched official source pages: WNYC's stream formats page, WFMU's mobile stream page, BBC's international listening guidance, KCRW's Eclectic24 page, Prasar Bharati's live-streaming page, and Akashvani's live-radio catalogue.
- WNYC's official source confirms the exact 93.9 MP3/AAC endpoints. WFMU's official source confirms its 128k/32k MP3 endpoints (published as HTTP). KCRW explicitly describes Eclectic24 as a 24-hour music service. RTÉ's official manifest list is from an older support article; the broadcaster says the old Radio Player is being retired on 16 Nov 2026 in favour of RTÉ Listen, so the legacy manifest candidates need special revalidation.
- Added WQXR and New Sounds to the research-only candidate audit because WNYC publishes their direct MP3/AAC endpoints. They have not been added to the Dev station selector and are not GREEN.
- No station was marked GREEN or RED. No station was removed. No Indian entry or PTT-priority behavior was changed.

### Audit implementation limitation

The current Dev page tests actual browser playback in five-minute background scans and shows only GREEN stations, but its `feedState` is currently in-memory and does not persist hourly failure streaks or a central test history. The Markdown audit is the cumulative record for this scheduled research run. The browser scanner cannot prove continuous service while the page is closed. Do not interpret its five-minute scan interval as a 24/7 uptime monitor.
 
## Removal policy

Do not delete any station from the selectable Dev source catalogue based on one failed check. Only consider removal after three consecutive hourly RED results with explicit HTTP 404/410 or equivalent confirmed invalid-source evidence. Preserve removed entries and their URLs in this file for restoration. CORS blocks, timeouts, geoblocking, unsupported browser formats, DNS failures in the audit runner, and inconclusive tests remain YELLOW.

## Implementation note

The Dev scanner now supports both HLS and direct MP3/AAC URLs. The station picker continues to show only GREEN stations. The browser's successful playback test is the authority for GREEN status; research evidence alone never upgrades a station to GREEN.
