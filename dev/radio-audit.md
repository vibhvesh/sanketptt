# Sanket PTT Dev — International Radio Stream Audit

Last updated: 2026-11-16 06:00 IST

## Status key

- **GREEN** — direct stream decoded and playback time advanced in a real browser test.
- **YELLOW** — candidate is reputable, but playback, CORS, format, geographic access, or continuous schedule is not yet verified.
- **RED** — repeatedly confirmed dead/invalid endpoint. A single timeout or a blocked test environment is never enough to mark RED.

## Current verified list

No GREEN streams yet. One RED service: WNYC 820 AM (officially discontinued). Sixteen other candidates remain YELLOW. No station has been removed from the Dev registry.

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


## Latest cumulative snapshot — 2026-11-16 02:47 IST

- **GREEN (0):** none. No candidate has passed an actual decoded-audio playback test.
- **YELLOW (15):** BBC World Service; WNYC 93.9 FM; WNYC 820 AM; WFMU Freeform; KCRW Eclectic24; ABC NewsRadio; RTÉ Radio 1; RTÉ 2FM; RTÉ Raidió na Gaeltachta; WQXR 105.9 FM; WNYC New Sounds; WNYC Operavore; WNYC New Standards; France Inter; franceinfo.
- **RED (0):** none. No candidate has three consecutive hourly checks with confirmed invalid origin responses.
- **Removed:** none. No Indian station entry or PTT priority behavior was changed.

## Station-by-station audit — 2026-11-16 02:47 IST

Test time below is the audit-run timestamp in India Standard Time. All candidates remain YELLOW because this run could not obtain decoded audio. "Reader result" describes the web content reader only and must not be treated as an origin-server verdict.

| Stream name | Country | Language | Official source | Direct stream URL / player | Test time | Manifest / HTTP evidence | Audio evidence | Status |
|---|---|---|---|---|---|---|---|---|
| BBC World Service | UK / international | English | BBC international listening guidance: https://help.bbc.com/hc/en-us/articles/42652680528659-Update-on-access-to-BBC-Sounds-outside-the-UK | Candidate: https://stream.live.vc.bbcmedia.co.uk/bbc_world_service (raw URL is directory-sourced, not published on the cited BBC help page) | 2026-11-16 02:47 IST | Direct range request failed at DNS before connecting; web reader could not fetch audio URL. No HTTP status or manifest. | No MP3/AAC bytes decoded; no browser playback-clock proof. | YELLOW |
| WNYC 93.9 FM | USA | English | WNYC stream formats: https://prod.wnyc.org/audio-other-formats/ | https://fm939.wnyc.org/wnycfm (MP3 64 kbps); https://fm939.wnyc.org/wnycfm.aac (AAC 32 kbps) | 2026-11-16 02:47 IST | Official formats page fetched and confirms both URLs. Direct stream range request failed at DNS; web reader declined the audio URL. | No MP3/AAC frames decoded. | YELLOW |
| WNYC 820 AM | USA | English | WNYC stream formats: https://prod.wnyc.org/audio-other-formats/ | https://am820.wnyc.org/wnycam (MP3 64 kbps); https://am820.wnyc.org/wnycam.aac (AAC 32 kbps) | 2026-11-16 02:47 IST | Official formats page lists both URLs. Web reader reported 404 for the MP3 endpoint once; audit runner could not resolve DNS, so this is not yet a corroborated origin failure. | No audio bytes decoded. | YELLOW |
| WFMU Freeform | USA | English | WFMU mobile stream information: https://freeform.wfmu.org/mobile.shtml | Dev candidate: https://stream0.wfmu.org/freeform-128k.mp3; broadcaster page publishes http://stream0.wfmu.org/freeform-128k.mp3 and a 32k alternative. | 2026-11-16 02:47 IST | Official page fetched and confirms direct MP3 streams. HTTPS candidate range request failed at DNS; web reader could not fetch the media URL. | No MP3 frames decoded. | YELLOW |
| KCRW Eclectic24 | USA | English | KCRW describes Eclectic24 as a 24-hour all-music stream: https://www.kcrw.com/shows/eclectic24/about | Candidate: https://kcrw.streamguys1.com/kcrw_192k_mp3_e24_internet_radio (raw URL is third-party sourced; KCRW page confirms the service but not this exact endpoint) | 2026-11-16 02:47 IST | Range request failed at DNS; web reader could not fetch media URL. No origin HTTP status. | No MP3 frames decoded. | YELLOW |
| ABC NewsRadio | Australia | English | ABC live player: https://www.abc.net.au/listen/live/news ; ABC third-party stream distribution guidance: https://help.abc.net.au/hc/en-us/articles/15071793950607-Changes-to-ABC-Radio-Live-Streams-on-Third-Party-Platforms | No stable direct URL published in the inspected official documentation; use official live player above. | 2026-11-16 02:47 IST | Official player page is accessible; ABC says third-party stream distribution is subject to changes and selected partner agreements. No direct endpoint available to test. | No direct audio endpoint to decode. | YELLOW |
| RTÉ Radio 1 | Ireland | English | RTÉ legacy internet-radio manifest help: https://www.rte.ie/radio/radio1/static/2021/0704/1232947-rte-radio-help-support/ ; RTÉ Listen migration notice: https://www.rte.ie/radio/support/2026/0728/1585419-rte-listen-support-contact/ | https://www.rte.ie/manifests/radio1.m3u8 | 2026-11-16 02:47 IST | Reader returned 403 for manifest. No manifest body was obtained. RTÉ says Radio Player stops working on 16 Nov 2026; this does not itself prove this manifest is dead. | No media segment fetched or decoded. | YELLOW |
| RTÉ 2FM | Ireland | English | Same RTÉ manifest support page and RTÉ Listen migration notice above. | https://www.rte.ie/manifests/2fm.m3u8 | 2026-11-16 02:47 IST | Reader returned 403 for manifest. No manifest body was obtained; migration-day compatibility remains uncertain. | No media segment fetched or decoded. | YELLOW |
| RTÉ Raidió na Gaeltachta | Ireland | Irish | Same RTÉ manifest support page and RTÉ Listen migration notice above. | https://www.rte.ie/manifests/rnag.m3u8 | 2026-11-16 02:47 IST | Reader returned 403 for manifest. No manifest body was obtained; migration-day compatibility remains uncertain. | No media segment fetched or decoded. | YELLOW |
| WQXR 105.9 FM | USA | English | WNYC stream formats: https://prod.wnyc.org/audio-other-formats/ | https://stream.wqxr.org/wqxr (MP3 128 kbps); https://stream.wqxr.org/wqxr.aac (AAC 48 kbps) | 2026-11-16 02:47 IST | Official formats page fetched and confirms both URLs. Direct range request failed at DNS; web reader could not fetch media URL. | No MP3/AAC frames decoded. | YELLOW |
| WNYC New Sounds | USA | English | WNYC stream formats: https://prod.wnyc.org/audio-other-formats/ | https://q2stream.wqxr.org/q2 (MP3 128 kbps); https://q2stream.wqxr.org/q2.aac (AAC 48 kbps) | 2026-11-16 02:47 IST | Official formats page fetched and confirms both URLs. Direct range request failed at DNS; web reader could not fetch media URL. | No MP3/AAC frames decoded. | YELLOW |
| WNYC Operavore | USA | English | WNYC stream formats: https://prod.wnyc.org/audio-other-formats/ | https://opera-stream.wqxr.org/operavore (MP3 128 kbps); https://opera-stream.wqxr.org/operavore.aac (AAC 48 kbps) | 2026-11-16 02:47 IST | Official formats page fetched and confirms both URLs. Web reader reported unsupported audio/mpeg content type (400); this indicates its reader cannot consume the media type, not that the stream is dead. Audit runner DNS failed. | No MP3/AAC frames decoded. | YELLOW |
| WNYC New Standards | USA | English | WNYC stream formats: https://prod.wnyc.org/audio-other-formats/ | https://tjc.wnyc.org/js-stream (MP3 128 kbps); https://tjc.wnyc.org/js-stream.aac (AAC 48 kbps) | 2026-11-16 02:47 IST | Official formats page fetched and lists both URLs. Web reader reported 404 for MP3 once; audit runner DNS failed, so origin failure is not independently corroborated. | No audio bytes decoded. | YELLOW |
| France Inter | France | French | Radio France official Open API brand catalogue: https://developers.radiofrance.fr/doc/en/tutorial-by-example/list-brands | https://icecast.radiofrance.fr/franceinter-midfi.mp3?id=openapi | 2026-11-16 02:47 IST | Official API documentation supplies the exact liveStream URL. Range request failed at DNS; web reader could not fetch the audio URL. | No MP3 frames decoded. | YELLOW |
| franceinfo | France | French | Radio France official Open API brand catalogue: https://developers.radiofrance.fr/doc/en/tutorial-by-example/list-brands | https://icecast.radiofrance.fr/franceinfo-midfi.mp3?id=openapi | 2026-11-16 02:47 IST | Official API documentation supplies the exact liveStream URL. Range request failed at DNS; web reader could not fetch the audio URL. | No MP3 frames decoded. | YELLOW |

### Test log — 2026-11-16 02:47 IST

- Re-fetched the current `dev/radio-audit.md` and `dev/index.html` from GitHub main before testing.
- Attempted HTTP byte-range requests (bytes 0–4095) with a browser-like User-Agent and ICY metadata disabled against 14 direct URLs in the candidate table. The audit runner failed DNS resolution before connecting for every request. No origin HTTP response, audio frame, HLS manifest body or media segment was received.
- Also probed two RNZ stream URLs discovered in a non-official mirrored copy of an RNZ audio-help page. They were not promoted into the cumulative station list because the original RNZ page could not be fetched for source verification.
- Opened all three RTÉ HLS manifests through the web reader; each returned reader-side 403. No manifest was obtained, so no HLS segment URL could be extracted or tested.
- Opened WNYC's official formats page successfully. It publishes the exact WNYC 93.9, WNYC 820, WQXR, New Sounds, Operavore and New Standards MP3/AAC URLs.
- The web reader returned 404 once for WNYC 820 MP3 and New Standards MP3, and a 400 "unsupported content-type: audio/mpeg" for Operavore. These reader results are not three independent origin checks and do not satisfy the RED policy.
- Opened Radio France's official Open API documentation; it explicitly publishes live MP3 URLs for France Inter and franceinfo.
- BBC's current international guidance confirms World Service English live listening is available via BBC.com and the BBC app; it does not publish the raw candidate CDN URL used by Dev. BBC Sounds closed to listeners outside the UK on 21 July 2025.
- RTÉ's official support notice says RTÉ Radio Player stops working on 16 November 2026 and is replaced by RTÉ Listen. The old manifest URLs are therefore migration-day candidates requiring a browser test, not automatically dead.
- No audio was decoded and no browser playback clock advanced in this run. **No GREEN or RED classifications were assigned.** The web reader's inability to consume audio and the runner's DNS failures are inconclusive, not broadcaster outages.
- KCRW's official page explicitly calls Eclectic24 a 24-hour all-music channel. No other candidate is newly described as 24/7 by this run; no continuous-operation claim is inferred from a live-player link alone.
- No station was removed. No existing Indian station entry, radio selector priority or PTT priority behavior was changed.



## Latest cumulative snapshot — 2026-11-16 03:03 IST

- **GREEN (0):** none. No feed has passed an actual decoded-audio test with playback progression.
- **YELLOW (15):** BBC World Service; WNYC 93.9 FM; WNYC 820 AM; WFMU Freeform; KCRW Eclectic24; ABC NewsRadio; RTÉ Radio 1; RTÉ 2FM; RTÉ Raidió na Gaeltachta; WQXR 105.9 FM; WNYC New Sounds; WNYC Operavore; WNYC New Standards; France Inter; franceinfo.
- **RED (0):** none. DNS failures, reader-side 403s, unsupported media responses and test-runner timeouts are not confirmed origin failures and do not count toward the three-consecutive-hourly RED rule.
- **Removed:** none. No selectable international entry was deleted; all Indian stations and PTT priority behavior remain unchanged.

## Re-test log — 2026-11-16 03:03 IST

### Method

- Re-fetched `dev/radio-audit.md` and `dev/index.html` from GitHub `main` before the audit.
- Attempted HTTP byte-range reads (bytes 0–4095) with `curl`, `Icy-MetaData: 0`, a browser-like User-Agent and short connection/overall timeouts against 14 direct candidate URLs: WNYC 93.9, WNYC 820, WQXR, New Sounds, Operavore, New Standards, WFMU, KCRW Eclectic24, France Inter, franceinfo, BBC World Service, and the three RTÉ HLS manifests.
- All completed direct requests returned `HTTP 000`, zero body bytes and no remote IP. The first requests emitted explicit `Could not resolve host` errors; the final RTÉ manifest attempt also returned curl exit 6 (DNS resolution failure). No origin HTTP response was received.
- Opened direct media URLs with the web reader. MP3 endpoints for WNYC, WFMU, WQXR/New Sounds/Operavore/New Standards, Radio France, BBC and KCRW were not accessible to that reader. All three RTÉ manifest opens returned reader-side 403 Forbidden. These are reader/proxy results, not verified origin responses.
- Successfully fetched current official information pages: WNYC's stream-format page, WFMU's mobile/live-stream page, KCRW's Eclectic24 page, ABC's live NewsRadio player and third-party stream policy, and BBC's international listening guidance.
- WNYC's official page continues to publish the MP3/AAC endpoint pairs for WNYC 93.9, WNYC 820, WQXR, New Sounds, Operavore and New Standards. WFMU's official pages continue to publish live 128k/32k MP3 and AAC stream choices. KCRW's current Eclectic24 page labels it a 24-hour show and describes it as a 24-hour all-music channel; its tracklist panel displayed "off air" in the reader snapshot, which is not proof that the audio endpoint is down.
- ABC's official third-party distribution notice (updated 21 July 2026) says ABC is changing distribution to meet obligations and directs listeners to ABC listen or selected formal partners. Its official NewsRadio live player is reachable as a web page, but no direct public stream URL was extracted or tested; it remains a player-only YELLOW candidate.
- BBC's current international guidance confirms World Service English live access through BBC.com and the BBC app. The raw CDN URL in this audit is not published by that help page and could not be tested directly.
- RTÉ's current Listen support page says the old RTÉ Radio Player stops working on 16 November 2026, while live radio remains available through rte.ie/radio. This is a migration warning for the three older manifest candidates, not proof that the manifests are invalid. The web reader's 403 and the audit runner's DNS failure provided no manifest body, so no media-segment URLs could be extracted.
- No HLS manifest body or media segment was retrieved. No MP3/AAC frame was decoded. `ffprobe` was available locally but had no media bytes to inspect. No browser playback clock could be observed in this non-browser audit runner.

### Station-by-station outcome at 03:03 IST

| Stream | Country | Language | Official source | Direct URL tested / player | Manifest or HTTP result | Audio-segment / decode result | Status |
|---|---|---|---|---|---|---|---|
| BBC World Service | UK / international | English | https://help.bbc.com/hc/en-us/articles/42652680528659-Update-on-access-to-BBC-Sounds-outside-the-UK | https://stream.live.vc.bbcmedia.co.uk/bbc_world_service | HTTP 000 / DNS resolution failure; web reader cannot consume media URL | No bytes or decoded audio; official BBC.com player access is documented separately | YELLOW |
| WNYC 93.9 FM | USA | English | https://prod.wnyc.org/audio-other-formats/ | https://fm939.wnyc.org/wnycfm | HTTP 000 / DNS resolution failure; official page confirms MP3 and AAC alternatives | No MP3/AAC frames decoded | YELLOW |
| WNYC 820 AM | USA | English | https://prod.wnyc.org/audio-other-formats/ | https://am820.wnyc.org/wnycam | HTTP 000 / DNS resolution failure; official page confirms MP3 and AAC alternatives | No MP3/AAC frames decoded | YELLOW |
| WFMU Freeform | USA | English | https://freeform.wfmu.org/mobile.shtml and https://freeform.wfmu.org/audiostream.shtml | https://stream0.wfmu.org/freeform-128k.mp3 | HTTP 000 / DNS resolution failure; official page confirms 128k/32k direct streams | No MP3 frames decoded | YELLOW |
| KCRW Eclectic24 | USA | English | https://www.kcrw.com/shows/eclectic24/latest | https://kcrw.streamguys1.com/kcrw_192k_mp3_e24_internet_radio | HTTP 000 / DNS resolution failure; official page currently labels the service 24-hour | No MP3 frames decoded; page tracklist widget said "off air" in reader snapshot only | YELLOW |
| ABC NewsRadio | Australia | English | https://www.abc.net.au/listen/live/news and https://help.abc.net.au/hc/en-us/articles/15071793950607-Changes-to-ABC-Radio-Live-Streams-on-Third-Party-Platforms | Official player only; no direct URL confirmed | Official player HTML reachable; no direct audio endpoint exposed to test | No direct media bytes decoded | YELLOW |
| RTÉ Radio 1 | Ireland | English | https://www.rte.ie/radio/support/2026/0728/1585419-rte-listen-support-contact/ | https://www.rte.ie/manifests/radio1.m3u8 | Reader-side 403; curl HTTP 000 / DNS failure; no manifest body | No HLS media segment fetched or decoded | YELLOW |
| RTÉ 2FM | Ireland | English | Same RTÉ Listen support page | https://www.rte.ie/manifests/2fm.m3u8 | Reader-side 403; curl HTTP 000 / DNS failure; no manifest body | No HLS media segment fetched or decoded | YELLOW |
| RTÉ Raidió na Gaeltachta | Ireland | Irish | Same RTÉ Listen support page | https://www.rte.ie/manifests/rnag.m3u8 | Reader-side 403; curl HTTP 000 / DNS failure; no manifest body | No HLS media segment fetched or decoded | YELLOW |
| WQXR 105.9 FM | USA | English | https://prod.wnyc.org/audio-other-formats/ | https://stream.wqxr.org/wqxr | HTTP 000 / DNS resolution failure; official page confirms MP3/AAC alternatives | No MP3/AAC frames decoded | YELLOW |
| WNYC New Sounds | USA | English | https://prod.wnyc.org/audio-other-formats/ | https://q2stream.wqxr.org/q2 | HTTP 000 / DNS resolution failure; official page confirms MP3/AAC alternatives | No MP3/AAC frames decoded | YELLOW |
| WNYC Operavore | USA | English | https://prod.wnyc.org/audio-other-formats/ | https://opera-stream.wqxr.org/operavore | HTTP 000 / DNS resolution failure; official page confirms MP3/AAC alternatives | No MP3/AAC frames decoded | YELLOW |
| WNYC New Standards | USA | English | https://prod.wnyc.org/audio-other-formats/ | https://tjc.wnyc.org/js-stream | HTTP 000 / DNS resolution failure; official page confirms MP3/AAC alternatives | No MP3/AAC frames decoded | YELLOW |
| France Inter | France | French | https://developers.radiofrance.fr/doc/en/tutorial-by-example/list-brands | https://icecast.radiofrance.fr/franceinter-midfi.mp3?id=openapi | HTTP 000 / DNS resolution failure | No MP3 frames decoded | YELLOW |
| franceinfo | France | French | https://developers.radiofrance.fr/doc/en/tutorial-by-example/list-brands | https://icecast.radiofrance.fr/franceinfo-midfi.mp3?id=openapi | HTTP 000 / DNS resolution failure | No MP3 frames decoded | YELLOW |

### Classification and repository decision

- **GREEN:** none. Official source documentation or a reachable player page is not a substitute for decoded audio.
- **YELLOW:** all 15 candidates. The test environment failed before origin connection; RTÉ's reader-side 403s do not establish an origin 403.
- **RED:** none. No origin 404/410 or other invalid response was independently confirmed, so no hourly RED failure streak was incremented.
- No station was removed or added to the selectable Dev list. No Indian station or PTT priority logic was changed.
- The current Dev browser scanner remains the only available way in this workflow to prove playback-clock advancement. Its state is in-memory and the page must be open; this audit runner cannot claim continuous uptime monitoring.


## Latest cumulative snapshot — 2026-11-16 04:17 IST

- **GREEN (0):** none. No candidate has passed a real audio decode and playback-clock test.
- **YELLOW (16):** BBC World Service; WNYC 93.9 FM; WFMU Freeform; KCRW Eclectic24; ABC NewsRadio (official player only); RTÉ Radio 1; RTÉ 2FM; RTÉ Raidió na Gaeltachta; WQXR 105.9 FM; WNYC New Sounds; WNYC Operavore; WNYC New Standards; France Inter; franceinfo; Deutsche Welle Radio English; Radio One 91FM (New Zealand).
- **RED (1):** WNYC 820 AM internet stream. WNYC's official notice says the AM internet stream was shut down on 22 March 2025. The current WNYC formats page still lists its old URL, so that page appears stale for this entry. This RED classification is based on the broadcaster's explicit discontinuation notice plus an earlier reader-side 404 observation; this run could not reach the origin because DNS resolution failed.
- **Removal gate:** no deletion. WNYC 820 AM is not present in the Dev station registry, and no candidate has three consecutive hourly origin-level failure checks. No existing Indian station or PTT priority behavior was changed.
- **Dev selection behavior:** the station registry still contains the existing seven international test candidates (BBC World Service, WNYC 93.9, WFMU, KCRW Eclectic24 and the three RTÉ services), but the selector only populates from stations whose scanner state is GREEN. These candidates remain non-selectable while YELLOW.

## Station-by-station re-test — 2026-11-16 04:17 IST

| Stream | Country | Language | Official source | Direct stream URL / player | Test time | Latest evidence: manifest / HTTP | Audio-segment / decode result | Status |
|---|---|---|---|---|---|---|---|---|
| BBC World Service | UK / international | English | https://help.bbc.com/hc/en-us/articles/42652680528659-Update-on-access-to-BBC-Sounds-outside-the-UK | Candidate CDN URL: https://stream.live.vc.bbcmedia.co.uk/bbc_world_service (not published in the cited BBC help page); official player: https://www.bbc.com/audio | 04:17 IST | Local curl: HTTP 000, DNS failure; web reader could not consume the media URL. BBC confirms World Service English live access via BBC.com and the BBC app. | No media bytes or decoded audio; no browser playback clock. | YELLOW |
| WNYC 93.9 FM | USA | English | https://prod.wnyc.org/audio-other-formats/ | https://fm939.wnyc.org/wnycfm (official MP3; AAC alternative https://fm939.wnyc.org/wnycfm.aac) | 04:17 IST | Local curl: HTTP 000, DNS failure; web reader could not consume the direct audio URL. WNYC's official formats page lists both formats. | No MP3/AAC frames decoded. | YELLOW |
| WNYC 820 AM | USA | English | https://wnyc.org/story/wnyc-am-stream-ending-march-22/ and https://prod.wnyc.org/audio-other-formats/ | Legacy URL: https://am820.wnyc.org/wnycam | 04:17 IST | WNYC explicitly says it shut down the AM internet stream on 22 March 2025. Its formats page still lists the legacy URL. Current local curl: HTTP 000 due DNS; earlier web-reader attempt returned a reader-side 404. | No current origin bytes or decode; service discontinuation is explicitly confirmed by WNYC. | RED — discontinued |
| WFMU Freeform | USA | English | https://freeform.wfmu.org/mobile.shtml | Official URL: http://stream0.wfmu.org/freeform-128k.mp3 (32k alternative: http://stream0.wfmu.org/freeform-32k.mp3) | 04:17 IST | Local curl against the HTTPS host: HTTP 000, DNS failure; web reader could not consume the audio URL. WFMU's own page publishes the direct MP3 URLs. | No MP3 frames decoded. | YELLOW |
| KCRW Eclectic24 | USA | English | https://www.kcrw.com/shows/eclectic24/latest | Candidate direct URL (not published in the opened official page): https://kcrw.streamguys1.com/kcrw_192k_mp3_e24_internet_radio; official player: https://www.kcrw.com/shows/eclectic24/latest | 04:17 IST | Local curl: HTTP 000, DNS failure; web reader could not consume the direct audio URL. KCRW's current page labels the service a 24-hour show and describes it as a 24-hour all-music channel. | No MP3 frames decoded. | YELLOW |
| ABC NewsRadio | Australia | English | https://www.abc.net.au/listen/live/news and https://help.abc.net.au/hc/en-us/articles/15071793950607-Changes-to-ABC-Radio-Live-Streams-on-Third-Party-Platforms | Official live player only: https://www.abc.net.au/listen/live/news; direct stream URL not resolved | 04:17 IST | Official player page is reachable in web search; ABC's July 2026 notice says it is changing third-party distribution and recommends ABC listen or selected formal partners. | No direct media URL available to test; no decoded audio. | YELLOW |
| RTÉ Radio 1 | Ireland | English | https://www.rte.ie/radio/support/2026/0728/1585419-rte-listen-support-contact/ | Legacy manifest: https://www.rte.ie/manifests/radio1.m3u8 | 04:17 IST | Local curl: HTTP 000, DNS failure; web reader returned 403 for the manifest. Reader-side 403 is not an origin response. RTÉ says the old Radio Player stops working on 16 November 2026 and is replaced by RTÉ Listen. | No manifest body, media-segment URLs or decoded audio. | YELLOW |
| RTÉ 2FM | Ireland | English | https://www.rte.ie/radio/support/2026/0728/1585419-rte-listen-support-contact/ | Legacy manifest: https://www.rte.ie/manifests/2fm.m3u8 | 04:17 IST | Local curl: HTTP 000, DNS failure; web reader returned 403 for the manifest. RTÉ migration notice applies to the old Radio Player. | No manifest body, media-segment URLs or decoded audio. | YELLOW |
| RTÉ Raidió na Gaeltachta | Ireland | Irish | https://www.rte.ie/radio/support/2026/0728/1585419-rte-listen-support-contact/ | Legacy manifest: https://www.rte.ie/manifests/rnag.m3u8 | 04:17 IST | Local curl: HTTP 000, DNS failure; web reader returned 403 for the manifest. RTÉ migration notice applies to the old Radio Player. | No manifest body, media-segment URLs or decoded audio. | YELLOW |
| WQXR 105.9 FM | USA | English | https://prod.wnyc.org/audio-other-formats/ | https://stream.wqxr.org/wqxr (official MP3; AAC alternative https://stream.wqxr.org/wqxr.aac) | 04:17 IST | Local curl: HTTP 000, DNS failure; direct media URL inaccessible to web reader. Official WNYC formats page lists MP3/AAC. | No MP3/AAC frames decoded. | YELLOW |
| WNYC New Sounds | USA | English | https://prod.wnyc.org/audio-other-formats/ | https://q2stream.wqxr.org/q2 (official MP3; AAC alternative https://q2stream.wqxr.org/q2.aac) | 04:17 IST | Local curl: HTTP 000, DNS failure; direct media URL inaccessible to web reader. Official WNYC formats page lists MP3/AAC. | No MP3/AAC frames decoded. | YELLOW |
| WNYC Operavore | USA | English | https://prod.wnyc.org/audio-other-formats/ | https://opera-stream.wqxr.org/operavore (official MP3; AAC alternative https://opera-stream.wqxr.org/operavore.aac) | 04:17 IST | Local curl: HTTP 000, DNS failure; direct media URL inaccessible to web reader. Official WNYC formats page lists MP3/AAC. | No MP3/AAC frames decoded. | YELLOW |
| WNYC New Standards | USA | English | https://prod.wnyc.org/audio-other-formats/ | https://tjc.wnyc.org/js-stream (official MP3; AAC alternative https://tjc.wnyc.org/js-stream.aac) | 04:17 IST | Local curl: HTTP 000, DNS failure; direct media URL inaccessible to web reader. Earlier reader-side 404 was not independently confirmed at origin. Official WNYC formats page lists MP3/AAC. | No MP3/AAC frames decoded. | YELLOW |
| France Inter | France | French | https://developers.radiofrance.fr/doc/en/tutorial-by-example/list-brands and https://developers.radiofrance.fr/doc/en/faq | https://icecast.radiofrance.fr/franceinter-midfi.mp3?id=openapi | 04:17 IST | Local curl: HTTP 000, DNS failure; web reader could not consume audio. Radio France publishes the URL in its API docs. Its API FAQ explicitly says the Open API is not authorised for live radio/podcast stream aggregation. | No MP3 frames decoded. Do not integrate into Sanket without separate written permission or an authorised player route. | YELLOW — rights/terms gate |
| franceinfo | France | French | https://developers.radiofrance.fr/doc/en/tutorial-by-example/list-brands and https://developers.radiofrance.fr/doc/en/faq | https://icecast.radiofrance.fr/franceinfo-midfi.mp3?id=openapi | 04:17 IST | Local curl: HTTP 000, DNS failure; web reader could not consume audio. Radio France publishes the URL in its API docs. Its API FAQ explicitly says the Open API is not authorised for live radio/podcast stream aggregation. | No MP3 frames decoded. Do not integrate into Sanket without separate written permission or an authorised player route. | YELLOW — rights/terms gate |
| Deutsche Welle Radio English | Germany / international | English | https://www.dw.com/downloads/49905237/dw-radio-streaming.pdf | https://dw.audiostream.io/dw/1002/mp3/64/dw-radio-english | 04:17 IST | Local curl: HTTP 000, DNS failure; web reader could not consume the URL. The official DW PDF is a 2024/25 schedule document and is not proof of current endpoint operation. | No MP3 frames decoded. The old PDF lists DW English 16:00–17:00 UTC daily in that schedule; do not claim 24/7. | YELLOW |
| Radio One 91FM | New Zealand | English | https://r1.coredev.nz/streaming | https://play.r1.co.nz/live | 04:17 IST | Local curl: HTTP 000, DNS failure. Web reader returned “unsupported content-type: audio/mpeg” (reader-side 400); this shows the endpoint is served as audio/mpeg to the reader but does not expose bytes for decoding. Official page advertises 192 kbps stereo MP3 and 24-hour worldwide streaming. | No audio bytes or decoded MP3 frames; no playback clock. | YELLOW |

### Test method and limitations — 04:17 IST

- Re-fetched the current audit file and Dev player from GitHub main before testing.
- Ran HTTP byte-range requests for bytes 0–65535 against all 16 direct URL candidates, following redirects, sending a browser-like User-Agent and disabling ICY metadata. The local audit runtime returned HTTP 000, zero bytes, empty content type and no remote IP for every URL. The failures were DNS resolution errors or DNS-resolution timeouts before an origin connection; these do not count as station failures.
- Opened direct media URLs through the web reader. Radio One 91FM returned a reader-side unsupported-content-type response for audio/mpeg; the three RTÉ manifests returned reader-side 403; the remaining direct media URLs were not readable by that tool. These responses do not prove origin errors.
- No HLS manifest body was retrieved, so no HLS media segments could be requested or decoded. No MP3/AAC frames were obtained. No browser media element or playback clock was available in this automation runtime.
- Therefore GREEN remains zero. YELLOW means the candidate or source is plausible but the stream was not proven playable here. WNYC 820 AM is RED only because WNYC explicitly discontinued that internet stream; no selector cleanup was performed.
- Radio France's published API documentation is a terms blocker for use as a third-party live-stream aggregator, even though the docs expose a liveStream field. Keep those URLs out of Sanket until authorised.
- WNYC's current formats page lists the old AM URL, but the station's own March 2025 discontinuation notice takes precedence. Do not use the stale AM URL.
- The Dev browser scanner remains the only path currently available in this workflow to prove actual decoded playback and playback-clock advancement. Its scan is page-session based; this run cannot claim continuous 24/7 monitoring.

### Repository decision — 04:17 IST

- No code changes to dev/index.html.
- No station removed from the selectable Dev list or candidate registry.
- WNYC 820 AM is not present in the Dev station registry; exact name lookup returned no match.
- Existing Indian stations and PTT priority behavior remain unchanged.
- No removed-station restore record was needed because no station was removed.


## Overnight consolidated re-test — 2026-11-16 06:00 IST

### Cumulative result

- **GREEN (0):** none. No feed has passed decoded audio plus advancing playback-clock verification.
- **YELLOW (16):** BBC World Service; WNYC 93.9 FM; WFMU Freeform; KCRW Eclectic24; ABC NewsRadio (official player only); RTÉ Radio 1; RTÉ 2FM; RTÉ Raidió na Gaeltachta; WQXR 105.9 FM; WNYC New Sounds; WNYC Operavore; WNYC New Standards; France Inter; franceinfo; Deutsche Welle Radio English; Radio One 91FM (New Zealand).
- **RED (1):** WNYC 820 AM internet stream — WNYC's own discontinuation notice says the AM internet stream ended on 22 March 2025. This is a service discontinuation classification, not a new HTTP failure in this run.
- **Removed from Dev selector:** none. WNYC 820 AM is not in the Dev station registry. No selectable station has accumulated three consecutive hourly origin-confirmed RED checks.

### Fresh direct-endpoint test — 06:00:49 IST

Test method:
- Re-tested 16 direct candidate URLs, including the discontinued WNYC 820 legacy URL, using concurrent curl HTTP byte-range requests for bytes 0–4095, a browser-like User-Agent, 2-second connection timeout and 3-second overall timeout.
- Followed redirects and recorded HTTP status, received bytes, remote IP and content type.
- All 16 attempts failed before an HTTP connection. WNYC 93.9 returned curl exit 6 (could not resolve host); the other 15 returned curl exit 28 (DNS resolution timed out at 3 seconds). Every request reported HTTP 000, zero bytes, no remote IP and no content type.
- This audit runner therefore received no origin response. These results are network-runner DNS failures, not evidence that the stations are down.
- No HLS manifest body was retrieved, so no HLS media-segment URL could be extracted or fetched. No MP3/AAC frames were received or decoded. No browser media element or playback clock was available.
- Separately opened six representative direct URLs in the web reader: WNYC 93.9, WFMU, KCRW, BBC World Service and Radio One were not accessible to that reader; RTÉ Radio 1 manifest returned reader-side 403. These are reader/proxy limitations, not origin HTTP results.

### Station-by-station re-test record

| Stream | Country | Language | Official source | Direct stream URL / official player | Test time | Manifest / HTTP evidence | Audio evidence | Status |
|---|---|---|---|---|---|---|---|---|
| BBC World Service | UK / international | English | https://help.bbc.com/hc/en-us/articles/42652680528659-Update-on-access-to-BBC-Sounds-outside-the-UK | Candidate CDN: https://stream.live.vc.bbcmedia.co.uk/bbc_world_service; official player: https://www.bbc.com/audio | 06:00:49 IST | curl exit 28, HTTP 000, DNS timeout; reader could not open audio URL | No bytes, frames or playback-clock test; BBC confirms international live access via BBC.com and app | YELLOW |
| WNYC 93.9 FM | USA | English | https://prod.wnyc.org/audio-other-formats/ | https://fm939.wnyc.org/wnycfm (MP3); https://fm939.wnyc.org/wnycfm.aac (AAC) | 06:00:49 IST | curl exit 6, HTTP 000, DNS resolution failure; reader could not open URL; official page lists MP3/AAC | No audio bytes or frames decoded | YELLOW |
| WNYC 820 AM | USA | English | https://wnyc.org/story/wnyc-am-stream-ending-march-22/ | Legacy URL: https://am820.wnyc.org/wnycam | 06:00:49 IST | curl exit 28, HTTP 000, DNS timeout; WNYC's discontinuation notice is stronger evidence than its stale format listing | No current audio received; service discontinued according to broadcaster | RED — discontinued |
| WFMU Freeform | USA | English | https://freeform.wfmu.org/mobile.shtml and https://freeform.wfmu.org/audiostream.shtml | http://stream0.wfmu.org/freeform-128k.mp3; alternate: http://stream0.wfmu.org/freeform-32k.mp3 | 06:00:49 IST | curl exit 28, HTTP 000, DNS timeout; reader could not open audio URL; official pages list direct MP3/AAC options | No MP3/AAC bytes or decoded frames | YELLOW |
| KCRW Eclectic24 | USA | English | https://www.kcrw.com/shows/eclectic24/latest | Candidate: https://kcrw.streamguys1.com/kcrw_192k_mp3_e24_internet_radio; official player: https://www.kcrw.com/shows/eclectic24/latest | 06:00:49 IST | curl exit 28, HTTP 000, DNS timeout; reader could not open direct audio. Official page currently shows on air and a live tracklist | Web page activity is not audio decode; no MP3 frames or playback-clock test | YELLOW |
| ABC NewsRadio | Australia | English | https://www.abc.net.au/listen/live/news and https://help.abc.net.au/hc/en-us/articles/15071793950607-Changes-to-ABC-Radio-Live-Streams-on-Third-Party-Platforms | Official player: https://www.abc.net.au/listen/live/news; direct endpoint not established | 06:00:49 IST | No direct URL to test; ABC directs listeners to ABC listen or formal partners because of third-party distribution changes | No direct audio endpoint decoded | YELLOW |
| RTÉ Radio 1 | Ireland | English | https://www.rte.ie/radio/support/2026/0728/1585419-rte-listen-support-contact/ | Legacy manifest: https://www.rte.ie/manifests/radio1.m3u8; current official destination: https://www.rte.ie/radio/ | 06:00:49 IST | curl exit 28, HTTP 000, DNS timeout; reader-side 403 on manifest. RTÉ Radio Player retirement date is 16 Nov 2026 | No manifest body, media segment or decoded audio | YELLOW |
| RTÉ 2FM | Ireland | English | https://www.rte.ie/radio/support/2026/0728/1585419-rte-listen-support-contact/ | Legacy manifest: https://www.rte.ie/manifests/2fm.m3u8; official destination: https://www.rte.ie/radio/ | 06:00:49 IST | curl exit 28, HTTP 000, DNS timeout; no origin manifest response | No media segment or decoded audio | YELLOW |
| RTÉ Raidió na Gaeltachta | Ireland | Irish | https://www.rte.ie/radio/support/2026/0728/1585419-rte-listen-support-contact/ | Legacy manifest: https://www.rte.ie/manifests/rnag.m3u8; official destination: https://www.rte.ie/radio/ | 06:00:49 IST | curl exit 28, HTTP 000, DNS timeout; no origin manifest response | No media segment or decoded audio | YELLOW |
| WQXR 105.9 FM | USA | English | https://prod.wnyc.org/audio-other-formats/ | https://stream.wqxr.org/wqxr (MP3); https://stream.wqxr.org/wqxr.aac (AAC) | 06:00:49 IST | curl exit 28, HTTP 000, DNS timeout; official WNYC formats page lists both formats | No MP3/AAC bytes or frames decoded | YELLOW |
| WNYC New Sounds | USA | English | https://prod.wnyc.org/audio-other-formats/ | https://q2stream.wqxr.org/q2 (MP3); https://q2stream.wqxr.org/q2.aac (AAC) | 06:00:49 IST | curl exit 28, HTTP 000, DNS timeout; official WNYC formats page lists both formats | No MP3/AAC bytes or frames decoded | YELLOW |
| WNYC Operavore | USA | English | https://prod.wnyc.org/audio-other-formats/ | https://opera-stream.wqxr.org/operavore (MP3); https://opera-stream.wqxr.org/operavore.aac (AAC) | 06:00:49 IST | curl exit 28, HTTP 000, DNS timeout; official WNYC formats page lists both formats | No MP3/AAC bytes or frames decoded | YELLOW |
| WNYC New Standards | USA | English | https://prod.wnyc.org/audio-other-formats/ | https://tjc.wnyc.org/js-stream (MP3); https://tjc.wnyc.org/js-stream.aac (AAC) | 06:00:49 IST | curl exit 28, HTTP 000, DNS timeout; official WNYC formats page lists both formats | No MP3/AAC bytes or frames decoded | YELLOW |
| France Inter | France | French | https://developers.radiofrance.fr/doc/en/tutorial-by-example/list-brands and https://developers.radiofrance.fr/doc/en/faq | https://icecast.radiofrance.fr/franceinter-midfi.mp3?id=openapi | 06:00:49 IST | curl exit 28, HTTP 000, DNS timeout | No MP3 frames decoded. Radio France API FAQ says its Open API is not authorised for third-party live stream aggregation; do not integrate without permission | YELLOW — rights/terms gate |
| franceinfo | France | French | https://developers.radiofrance.fr/doc/en/tutorial-by-example/list-brands and https://developers.radiofrance.fr/doc/en/faq | https://icecast.radiofrance.fr/franceinfo-midfi.mp3?id=openapi | 06:00:49 IST | curl exit 28, HTTP 000, DNS timeout | No MP3 frames decoded. Radio France API FAQ says its Open API is not authorised for third-party live stream aggregation; do not integrate without permission | YELLOW — rights/terms gate |
| Deutsche Welle Radio English | Germany / international | English | https://www.dw.com/downloads/49905237/dw-radio-streaming.pdf | https://dw.audiostream.io/dw/1002/mp3/64/dw-radio-english | 06:00:49 IST | curl exit 28, HTTP 000, DNS timeout; official schedule PDF is historical, not current endpoint proof | No MP3 frames decoded; no current 24/7 claim | YELLOW |
| Radio One 91FM | New Zealand | English | https://r1.coredev.nz/streaming | https://play.r1.co.nz/live | 06:00:49 IST | curl exit 28, HTTP 000, DNS timeout; earlier reader returned audio/mpeg unsupported-content response | No audio bytes or decoded MP3 frames | YELLOW |

### Fresh official-source checks — 05:59–06:00 IST

- KCRW's live Eclectic24 page was fetched successfully and showed on air plus a current tracklist. KCRW explicitly describes Eclectic24 as a 24-hour all-music channel. This verifies current programme-page activity and the stated schedule, not the candidate MP3 endpoint itself.
- WNYC's official formats page still lists direct MP3/AAC endpoints for WNYC 93.9, WNYC 820, WQXR, New Sounds, Operavore and New Standards. The stale WNYC 820 listing is overridden by the station's explicit March 2025 discontinuation notice.
- WFMU's official mobile and stream pages list direct MP3 and AAC stream options, including 128k and 32k MP3.
- ABC's July 2026 notice says its third-party stream distribution is changing and directs listeners to ABC listen or selected partners; do not scrape the app's undocumented media URLs.
- BBC confirms World Service English remains internationally available through BBC.com and the BBC app; the candidate raw CDN URL is not published by the cited BBC help page.
- RTÉ's current support page says RTÉ Radio Player stops working on 16 November 2026 and is replaced by RTÉ Listen. Treat the three older manifest URLs as legacy candidates until a fresh official endpoint is documented and decoded.

### Dev safety verification

- Re-fetched current dev/index.html before and after this audit: blob SHA remains a93b3278e399fd55941e2e3392c14114d8327497.
- No code or selectable station entry changed.
- No station deletion or registry cleanup was performed.
- Existing Indian stations and PTT priority behavior remain untouched.
- No removed-station restore record was needed.
- The Dev browser scanner still requires the page to be open and uses in-memory status; it is not a persistent 24/7 monitor. This automation's network runner currently cannot resolve the stream hosts, so it cannot provide the required decoded-audio GREEN proof.



## Morning consolidated re-test — 2026-11-16 06:46:23 IST

### Cumulative classification

- **GREEN (0):** none. No candidate has passed a real audio decode plus advancing playback-clock test.
- **YELLOW (16):** BBC World Service; WNYC 93.9 FM; WFMU Freeform; KCRW Eclectic24; ABC NewsRadio; RTÉ Radio 1; RTÉ 2FM; RTÉ Raidió na Gaeltachta; WQXR 105.9 FM; WNYC New Sounds; WNYC Operavore; WNYC New Standards; France Inter; franceinfo; Deutsche Welle Radio English; Radio One 91FM (New Zealand).
- **RED (1):** WNYC 820 AM internet stream — WNYC's own notice says the AM internet stream ended on 22 March 2025. The stale URL still appears on the formats page, but the discontinuation notice takes precedence.
- **Dev selector removals:** none. WNYC 820 AM is not in the Dev station registry. No selectable station has three consecutive hourly origin-confirmed RED checks.

### Direct endpoint re-test — 06:46:23 IST

Method:
- Re-tested 17 URLs (the 16 YELLOW candidates plus the discontinued WNYC 820 legacy URL) with `curl -L`, HTTP byte range `0-4095`, 2-second connect timeout and 4-second overall timeout. Captured HTTP status, downloaded bytes, content type, remote IP and curl exit code.
- All 17 tests ended before receiving an origin HTTP response: HTTP 000, 0 bytes, empty content type and no remote IP. Fifteen timed out during DNS resolution (curl exit 28); WFMU Freeform and franceinfo returned explicit DNS resolution errors (curl exit 6). These are test-runner network failures, not station outages.
- Separately attempted direct URL opens through the web reader for WNYC 93.9, WFMU, KCRW Eclectic24, Radio One 91FM, BBC World Service and the RTÉ Radio 1 manifest. The five direct audio URLs were inaccessible to the reader; RTÉ Radio 1 returned reader-side 403. These are not verified broadcaster-origin responses.
- No HLS manifest body was retrieved, so no HLS media segments could be extracted or decoded. No MP3/AAC frames were obtained. No browser media element or playback clock was available in this run.

### Station-by-station record — 06:46:23 IST

| Stream | Country | Language | Official source | Direct stream URL / official player | Test time | Latest test evidence | Cumulative status |
|---|---|---|---|---|---|---|---|
| BBC World Service | UK / international | English | https://help.bbc.com/hc/en-us/articles/42652680528659-Update-on-access-to-BBC-Sounds-outside-the-UK | Candidate: https://stream.live.vc.bbcmedia.co.uk/bbc_world_service ; official player: https://www.bbc.com/audio/stations | 06:46:23 IST | curl 28, HTTP 000, DNS timeout; web reader could not open direct audio URL; no bytes or playback test | YELLOW |
| WNYC 93.9 FM | USA | English | https://prod.wnyc.org/audio-other-formats/ | https://fm939.wnyc.org/wnycfm (MP3); https://fm939.wnyc.org/wnycfm.aac (AAC) | 06:46:23 IST | curl 28, HTTP 000, DNS timeout; web reader could not open direct URL; official formats page lists MP3/AAC | YELLOW |
| WNYC 820 AM | USA | English | https://wnyc.org/story/wnyc-am-stream-ending-march-22/ | Legacy: https://am820.wnyc.org/wnycam | 06:46:23 IST | curl 28, HTTP 000, DNS timeout; broadcaster confirms internet stream discontinued 22 Mar 2025 | RED — discontinued |
| WFMU Freeform | USA | English | https://www.wfmu.org/audiostream.shtml and https://freeform.wfmu.org/mobile.shtml | http://stream0.wfmu.org/freeform-128k.mp3 ; alternate: http://stream0.wfmu.org/freeform-32k.mp3 | 06:46:23 IST | curl 6, HTTP 000, DNS resolution failure; web reader could not open direct URL; official pages publish MP3/AAC options | YELLOW |
| KCRW Eclectic24 | USA | English | https://www.kcrw.com/shows/eclectic24/latest | Candidate: https://kcrw.streamguys1.com/kcrw_192k_mp3_e24_internet_radio ; official player: https://www.kcrw.com/shows/eclectic24/latest | 06:46:23 IST | curl 28, HTTP 000, DNS timeout; reader could not open direct audio; official page fetched successfully and showed current tracklist / on-air state | YELLOW |
| ABC NewsRadio | Australia | English | https://help.abc.net.au/hc/en-us/articles/15071793950607-Changes-to-ABC-Radio-Live-Streams-on-Third-Party-Platforms | Official player: https://www.abc.net.au/listen/live/news ; no approved direct URL established | 06:46:23 IST | curl 28, HTTP 000, DNS timeout on official player page; ABC says third-party distribution is changing and directs listeners to ABC listen / approved partners | YELLOW |
| RTÉ Radio 1 | Ireland | English | https://www.rte.ie/radio/support/2026/0728/1585419-rte-listen-support-contact/ and https://www.rte.ie/radio/radio1/static/2021/0704/1232947-rte-radio-help-support/ | Legacy manifest: https://www.rte.ie/manifests/radio1.m3u8 ; current web player: https://www.rte.ie/radio/ | 06:46:23 IST | curl 28, HTTP 000, DNS timeout; web reader returned 403 on manifest; RTÉ says old Radio Player retires 16 Nov 2026, while live radio remains on rte.ie/radio | YELLOW |
| RTÉ 2FM | Ireland | English | https://www.rte.ie/radio/support/2026/0728/1585419-rte-listen-support-contact/ and https://www.rte.ie/radio/radio1/static/2021/0704/1232947-rte-radio-help-support/ | Legacy manifest: https://www.rte.ie/manifests/2fm.m3u8 ; current web player: https://www.rte.ie/radio/ | 06:46:23 IST | curl 28, HTTP 000, DNS timeout; no manifest body or media segments | YELLOW |
| RTÉ Raidió na Gaeltachta | Ireland | Irish | https://www.rte.ie/radio/support/2026/0728/1585419-rte-listen-support-contact/ and https://www.rte.ie/radio/radio1/static/2021/0704/1232947-rte-radio-help-support/ | Legacy manifest: https://www.rte.ie/manifests/rnag.m3u8 ; current web player: https://www.rte.ie/radio/ | 06:46:23 IST | curl 28, HTTP 000, DNS timeout; no manifest body or media segments | YELLOW |
| WQXR 105.9 FM | USA | English | https://prod.wnyc.org/audio-other-formats/ | https://stream.wqxr.org/wqxr (MP3); https://stream.wqxr.org/wqxr.aac (AAC) | 06:46:23 IST | curl 28, HTTP 000, DNS timeout; no media bytes; official WNYC formats page lists both formats | YELLOW |
| WNYC New Sounds | USA | English | https://prod.wnyc.org/audio-other-formats/ | https://q2stream.wqxr.org/q2 (MP3); https://q2stream.wqxr.org/q2.aac (AAC) | 06:46:23 IST | curl 28, HTTP 000, DNS timeout; no media bytes; official formats page lists both formats | YELLOW |
| WNYC Operavore | USA | English | https://prod.wnyc.org/audio-other-formats/ | https://opera-stream.wqxr.org/operavore (MP3); https://opera-stream.wqxr.org/operavore.aac (AAC) | 06:46:23 IST | curl 28, HTTP 000, DNS timeout; no media bytes; official formats page lists both formats | YELLOW |
| WNYC New Standards | USA | English | https://prod.wnyc.org/audio-other-formats/ | https://tjc.wnyc.org/js-stream (MP3); https://tjc.wnyc.org/js-stream.aac (AAC) | 06:46:23 IST | curl 28, HTTP 000, DNS timeout; no media bytes; official formats page lists both formats | YELLOW |
| France Inter | France | French | https://developers.radiofrance.fr/doc/en/tutorial-by-example/list-brands and https://developers.radiofrance.fr/doc/en/faq | https://icecast.radiofrance.fr/franceinter-midfi.mp3?id=openapi | 06:46:23 IST | curl 28, HTTP 000, DNS timeout; no MP3 frames. Radio France FAQ explicitly says its Open API is not authorised for live radio/podcast stream applications | YELLOW — rights/terms gate |
| franceinfo | France | French | https://developers.radiofrance.fr/doc/en/tutorial-by-example/list-brands and https://developers.radiofrance.fr/doc/en/faq | https://icecast.radiofrance.fr/franceinfo-midfi.mp3?id=openapi | 06:46:23 IST | curl 6, HTTP 000, DNS resolution failure; no MP3 frames. Radio France Open API is not authorised for live-stream aggregation | YELLOW — rights/terms gate |
| Deutsche Welle Radio English | Germany / international | English | https://static.dw.com/downloads/77193712/A26_Radio_overview.pdf | https://dw.audiostream.io/dw/1002/mp3/64/dw-radio-english | 06:46:23 IST | curl 28, HTTP 000, DNS timeout; no MP3 frames. Official Summer 2026 radio schedule expired 24 Oct 2026 and listed DW English 16:00–17:00 UTC daily; no 24/7 claim | YELLOW |
| Radio One 91FM | New Zealand | English | https://r1.coredev.nz/streaming | https://play.r1.co.nz/live | 06:46:23 IST | curl 28, HTTP 000, DNS timeout; web reader could not open direct URL; official page advertises 192 kbps stereo MP3 and 24-hour worldwide streaming | YELLOW |

### Fresh official-source findings — 06:40–06:46 IST

- **KCRW Eclectic24:** KCRW's live page was fetched successfully and showed an on-air tracklist at crawl time. KCRW describes Eclectic24 as a 24-hour all-music service. This verifies the published schedule and page activity, not successful decoding of the direct MP3 URL. Sources: https://www.kcrw.com/shows/eclectic24/latest and https://www.kcrw.com/shows/eclectic24/about
- **WNYC family:** WNYC's official formats page publishes MP3/AAC endpoints for 93.9, WQXR, New Sounds, Operavore and New Standards. The WNYC AM 820 entry remains stale because the station separately confirms the internet stream ended 22 March 2025. Sources: https://prod.wnyc.org/audio-other-formats/ and https://wnyc.org/story/wnyc-am-stream-ending-march-22/
- **WFMU:** Its current stream page still lists 128k AAC, 128k MP3 and 32k MP3 choices, and its mobile page gives direct MP3 URLs. Sources: https://www.wfmu.org/audiostream.shtml and https://freeform.wfmu.org/mobile.shtml
- **BBC:** BBC Sounds closed outside the UK on 21 July 2025. BBC says BBC World Service English and Radio 4 remain accessible via BBC.com and the BBC app; use the official international audio directory rather than assuming the BBC Sounds app works abroad. Sources: https://help.bbc.com/hc/en-us/articles/42652680528659-Update-on-access-to-BBC-Sounds-outside-the-UK and https://help.bbc.com/hc/en-us/articles/52290365445779-How-do-I-access-BBC-Audio-content
- **ABC:** ABC's 21 July 2026 notice says third-party live stream distribution is changing; ABC listen is the supported route. No approved direct NewsRadio URL was established in this pass. Source: https://help.abc.net.au/hc/en-us/articles/15071793950607-Changes-to-ABC-Radio-Live-Streams-on-Third-Party-Platforms
- **RTÉ:** RTÉ's support page says Radio Player stops working on 16 November 2026 and is replaced by RTÉ Listen. RTÉ's current website still offers live radio at rte.ie/radio, and its radio help page continues to document M3U/M3U8 URLs for internet radio devices. The legacy manifest must be retested from a real browser/worker before being labelled dead. Sources: https://www.rte.ie/radio/support/2026/0728/1585419-rte-listen-support-contact/ and https://www.rte.ie/radio/radio1/static/2021/0704/1232947-rte-radio-help-support/
- **Radio France:** The official API FAQ explicitly says the Open API is not authorised for live radio or podcast stream applications. It documents an official playerUrl field for embedding its autonomous player; use that route only if its terms and station permissions are satisfied. Source: https://developers.radiofrance.fr/doc/en/faq
- **Deutsche Welle:** The official Summer 2026 radio overview lists DW English 16:00–17:00 UTC daily for the schedule ending 24 October 2026. That schedule is expired; a current winter schedule and endpoint need to be confirmed before relying on it. Source: https://static.dw.com/downloads/77193712/A26_Radio_overview.pdf
- **Radio One 91FM:** The official station page advertises 192 kbps stereo MP3, worldwide access and a 24-hour stream, and publishes https://play.r1.co.nz/live. Source: https://r1.coredev.nz/streaming

### Monitoring and Dev safety review

- Re-fetched `dev/index.html`: blob SHA remains `a93b3278e399fd55941e2e3392c14114d8327497`; no player code was changed.
- The Dev registry contains seven international candidates (BBC World Service, WNYC 93.9, WFMU, KCRW Eclectic24 and the three RTÉ feeds). WNYC 820 AM is not present. Existing Indian entries remain present.
- The browser scanner uses a muted HTML audio element and only calls a feed green after `readyState >= 2`, `currentTime > 0.75` and the media is no longer paused. This is a meaningful browser playback proof. However, scanner results are held in page memory and auto-rescan every five minutes while the page is open; they are not a central hourly history.
- The selector is populated only from `feedState[id] === "green"`, so yellow and red entries are hidden from selection after a page scan. The scanner can label HLS 404/410 red on a single fatal response; it does not enforce three consecutive hourly failures. No station was removed or deleted in this audit. The three-hourly-failure removal rule therefore remains unimplemented in the Dev runtime; do not delete or hide a registry entry as a cleanup action based on this run.
- The separate `.github/workflows/radio-directory.yml` workflow is scheduled every 30 minutes, but it refreshes the Akashvani directory from `codito/akashvani`, not this international audit. Its script `scripts/refresh_radio_directory.py` references `seen` in the final payload/print even though it defines `unique`, causing a NameError before writing the refreshed JSON. I did not modify this workflow or script because it is a separate Indian directory path and the user's preservation constraint applies.
- No station was deleted. No existing Indian station was removed. PTT priority behavior was not changed. No restore record was needed.

### Decision

Keep GREEN at zero, retain all 16 international candidates as YELLOW, and retain WNYC 820 AM as RED in the audit only. Do not promote or delete stations until an external browser/network runner can fetch the real media, decode audio, and persist three consecutive hourly results for any proposed RED cleanup.
