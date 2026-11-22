# Sanket Radios + PTT audit

Audit date: 2026-11-22
Repository: vibhvesh/sanketptt
Scope: public radio experiences and their PTT entry points.

## Required behaviour
- No voice-search button, voice-search status panel, or SpeechRecognition-based station search in radio discovery.
- Text search and country/category/location filters remain available.
- Each of the five radio experiences exposes the same Sanket PTT line connection.
- Radio playback continues while the PTT line is connected and listening.
- Incoming PTT audio and local transmission take priority over internet radio.
- When PTT activity ends, the selected internet-radio station resumes.
- PTT channel identity and the selected audio output are preserved.

## Experience-by-experience review

| Experience | Route | Implementation | Review status |
|---|---|---|---|
| Command Radio | /god-mode-radio/?mode=command | Shared God Mode radio directory + embedded /radio/ PTT client | PTT panel moved directly below the radio player; code committed |
| Local Pulse | /god-mode-radio/?mode=local | Same shared page; nearby/regional preset | Inherits the same PTT panel and audio-priority logic |
| Soundwave | /god-mode-radio/?mode=music | Same shared page; music preset | Inherits the same PTT panel and audio-priority logic |
| Newsroom | /god-mode-radio/?mode=news | Same shared page; news/talk preset | Inherits the same PTT panel and audio-priority logic |
| Worldlink | /god-mode-radio/?mode=world | Same shared page; international preset | Inherits the same PTT panel and audio-priority logic |

## Related pages and components

| Page/component | Route or source | Purpose | Review status |
|---|---|---|---|
| God Mode workspace | /god-mode-radio/ | Shared radio player, station discovery, PTT connection and output selection | PTT panel repositioned above station discovery results, immediately after player |
| Standalone PTT-mode copy | /god-mode-radio/ptt-mode.html | Alternate workspace copy | Synced to the updated God Mode source |
| Main homepage | / | Embeds the shared God Mode workspace | Inherits shared PTT experience |
| Radio hub | /radios/ | Entry page for all five radio modes | Removed “voice-led discovery”; now describes text search |
| Command PTT client | /radio/ | Core PTT client embedded by God Mode | Existing client sends floor/activity state to parent; autojoin supported |
| Public radio directory | /radio-directory/ | Catalogue-only search/list page, not a live radio player | Links to God Mode; PTT is intentionally not embedded in this catalogue page |
| Guest PTT selector | /sanket-radios/ | Public PTT line selection | PTT utility, not an internet-radio discovery mode |
| Legacy Smart Radio | /smart-radio/ | Separate legacy radio experience | Not one of the five current radio modes; requires separate product decision before migrating/removing |
| Boondock radio skins | /boondock/radio/ and device-specific subroutes | Legacy/device-specific PTT interfaces | Separate PTT clients; not the five public internet-radio experiences |

## Code changes committed in this audit

- `89756f71fed600884e9370cf048da2884e0bac48` — moved the PTT connection panel to directly below the radio player so users see CONNECT PTT without scrolling past station results.
- `8f7a7f6183f824f22abeddc087e7e7d2c5063213` — removed voice-led wording from the five-radio hub.
- `479198e7b3e212406fbfd7814dc1bb473bd98f46` — synced the standalone PTT-mode page with the updated God Mode page.

## Verification still required

GitHub source changes are committed. A live browser/device test is still required to confirm:
1. The deployed page reflects the latest source (the supplied screenshot showed an older UI without the PTT panel).
2. CONNECT PTT joins the selected channel and stays listening.
3. Incoming PTT audio pauses/ducks internet radio and is audible.
4. Local PTT transmission pauses/ducks internet radio.
5. Releasing the PTT floor resumes the previously selected station.
6. Speaker/headset/Bluetooth output selection applies to both radio and PTT audio.
7. All five mode URLs behave consistently on Android Chrome and desktop browsers.

Do not treat a GitHub commit as proof of live deployment or end-to-end audio verification.
