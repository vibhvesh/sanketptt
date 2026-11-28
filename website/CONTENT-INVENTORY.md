# Sanket website content inventory

Preview publishes `website/` from `dev` to `https://sanketptt.com/preview/`. Production (`main`) is a separate deploy. This list is the source for the frontline rebuild: routes stay, prices stay, and the functional clients stay.

Contact on every public page: Akshat Singh, akshatsingh@canberravision.com, akshat@sanketptt.com, +91 99982 99023, Canberra Vision, 713 Samanvay Silver, Akota, Vadodara, Gujarat, India.

## Products and prices

| Offering | Route | What it does | Price / CTA | Must keep working |
| --- | --- | --- | --- | --- |
| Sanket Cloud line | `/` `#pricing` | Hosted push-to-talk line. Unlimited live PTT. Latest 1 hour of recordings kept; older audio rolls off. | ₹450 per line / month. CTA: Choose Cloud. | Pricing copy. Contact mailto draft. |
| Extra retention | `/` `#pricing` | Adds recording time beyond the cloud hour. | ₹100 / month per extra 10 hours. | Same. |
| Retention Pro | `/` `#pricing` | Longer recording window on a line. | ₹150 per line / month for 30 days. | Same. |
| Transcription + translation | `/` `#pricing`, `/transcribe/` | Gujarati, Hindi and English transcription and translation. | ₹199 per 300 minutes. | `POST https://stlu-001.sanketptt.com/api/transcribe` (raw audio/wav, `X-Sanket-Language`, `X-Sanket-Translate`). Local Whisper fallback where the client already has it. |
| Dispatcher console seat | `/` `#pricing` | One dispatcher seat. | ₹999 / month. | Contact CTA. |
| SDR / radio gateway bridge | `/` `#pricing`, `/` `#sdr` | Bridge a radio or SDR gateway. Sanket SDR is for authorised military and defence use. | Ask for price. Product CTA: Request a meeting. | Do not invent a price. |
| Volume | `/` `#pricing` | Discount terms. | 10% off 25+ lines. 15% off 100+ lines. 2 months free on annual billing. | Keep the sentence in the pricing note. |
| Dedicated Server | `/` `#pricing` | Hardware and software for 100 lines. No recurring licence fee. | ₹5.66 lakh one-time. Priority support and updates ₹100 per user / month. | Same. |
| Sanket Local 20 | `/` `#pricing` | Customer-side hardware, 20 channels / 20 concurrent users. | ₹35,000 / year. | Same. |
| Sanket Local 50 | `/` `#pricing` | Local PTT server, local Whisper, transcription updates, no recurring licence. | ₹55,000 one-time. | Same. |
| Sanket Enterprise 200 | `/` `#pricing` | Self-hosted GPU transcription, from 200 channels, quoted up to 500. | From ₹5,50,000 one-time. | Note: enterprise still starts at ₹5,50,000 for 200 channels. |
| Sanket आकाशवाणी | `/aakashvani/` | Public-address control room. Raspberry Pi software, 4 AUX outputs. Four PTT inputs and four speaker outputs. PTT charges are separate; free channels may be used. | ₹35,000 one-time. CTA: Open control room. | In-page tabs (lines, routing, broadcast, alerts, hardware, recordings, settings). Preview values are illustrative. Alert rules are examples, not a live SOS service. |
| SanketVaani | `/` `#vaani` | Learning agent that compares a local model with a leading model. | Ask for price. | No checkout. |
| Sanket PTT (browser radio) | `/radio/` | Push-to-talk, presence, floor control, SSTV, GPS share, session log. | Open PTT. Channel login. | MQTT brokers in the page. `?ch=` joins a channel. `?embed=1` is the compact face used by older demos. |
| PTT 2 | `/ptt2/` | Current radio: channel picker above the PTT button, call sign, relay sign-in, device linking, transcription settings, GPS, SSTV. | Open PTT 2. | `POST https://relay.canberravision.com/api/auth/login`. Token in memory/session. Remember-me only stores the password when checked. Free mode `?free=1&ch=` joins with no email form. `RM-*` uses the relay and a background guest session from `sanket-radios/guest.js`. Other channels use the public MQTT path. `?embed=1` is the compact embed and must not show a theme pill. |
| Sanket Radios | `/sanket-radios/` | Lists free channels and builds share links. | Free. Open radio / Copy / Share / WhatsApp. | Share links are `…/ptt2/?free=1&ch=…` from the page origin. Instructions: pick, share, hold PTT. Public-channel warning. |
| Try it | `/try/` | Channel tabs with PTT and transcribe side by side. | Open a demo channel. | `try/try.js` plus `ptt/links.js`. |
| Demo console | `/demo.html` | Full-height PTT and transcribe split. Invite copies or shares the channel URL. | Invite / Share. | `?ch=` selects the channel. Default `sanket-website-demo`. |
| Live homepage demo | `/` `#live-demo` | Embedded free PTT 2 on the virtual channel. | Hold PTT after a call sign. | iframe `ptt2/?free=1&ch=virtual&embed=1`. No theme control inside the frame. |
| Sanket Transcribe | `/transcribe/` | Live transcription handset. Keyword list includes mayday, sos, emergency, चेतावनी. | Open Transcribe. | Same transcribe API and local fallback. |
| Boondock Echo | `/boondock/`, `/boondock/radio/` | Transcription handset and LTE-style radio copied onto this site. | Open the radio page. | `boondock/radio/` skins: Baofeng, Hytera, Kenwood, Motorola, Sonim, Boondock Echo LTE. |
| DMR monitor | `/dmr/`, `/dev/dmr/` | Talkgroup shortcuts and a custom numeric ID. Opens Hose. | Open DMR. | Brandmeister and Hose links in `ptt/links.json`. |
| Smart Radio | `/smart-radio/` | Search Radio Browser, preview a stream, save a station against a channel name in this browser. | Scan directory. PTT transmit stays disabled until a live channel session exists. | Radio Browser hosts `de1`, `fr1`, `nl1` `api.radio-browser.info`. Assignments are local only. The page must keep saying the server bridge is not broadcasting yet. |
| Development radio | `/dev/` | Development PTT with the Hindi radio scanner and bridge. | Open dev. | Do not point visitors at the old GitHub Pages copy. |
| Radio hub | `/radio-hub.html` | Directory of channels, apps, and source repositories. | Open channel / source. | Custom channel field uses `ptt/links.js` `sanitizeChannel`. Public-channel warning. |
| IT Intelligence | `/it-intelligence/` | Shared test asset register. | Add asset. | Supabase table `assets`. Public test data. Not a customer list. |
| SQL lab | `/it-intelligence/sql-lab.html` | Read-only SQL practice against the test database. | Run query. | Existing connection in the page. |
| AI copilot | `/it-intelligence/ai-copilot.html` | Plain-English questions over the test schema. | Ask. | Existing page script. |
| Leads desk | `/leads/` | Internal lead search. `noindex`. Not in the public menu. | Shared password gate. | `leads/config.js` and `leads/leads.js`. |
| Link book | `/ptt/links.json`, `/ptt/links.js`, `/ptt/apply.js` | Rewrites `data-link` targets and channel URLs. | None. | `scripts/check-links.sh` must stay green. Preview deploy rewrites `https://sanketptt.com/` to `/preview/`. |

## Industry routing

These pages only arrange the products above. They do not add customers, counts, or quotes.

| Page | Route | Built from |
| --- | --- | --- |
| Security | `/industries/security.html` | Channels, GPS share, transcription keywords (including sos), dispatcher seat, SDR meeting request. |
| Logistics and transport | `/industries/logistics.html` | Cloud line, free share links, browser on 4G/Wi-Fi, dispatcher seat. |
| Events | `/industries/events.html` | Free radios, public-channel warning, Sanket आकाशवाणी. |
| Government and public safety | `/industries/government.html` | Dedicated server, Local 20/50, Enterprise 200, आकाशवाणी, DMR monitor. |
| Developers | `/industries/developers.html` | PTT 2 modules, link book, transcribe API, Try, Smart Radio bridge note, IT Intelligence test desk. |

## Proof that is allowed on the homepage

- About 1 second to talk once you are on the channel.
- Cloud is ₹450 per line per month.
- The browser clients work on 4G and Wi-Fi.
- Made in Vadodara.
- Optional comparison line: from ₹450 per line, typical global PTT apps are about $6–$15 per user. Do not name a competitor or invent a tariff.

## Out of scope for this rebuild

PTT client behaviour, relay login, free-mode join, transcribe requests, Boondock skins, and the Smart Radio search stay in their existing files. The new CSS is limited to the marketing shell so a theme pill cannot sit on the PTT 2 or embedded radio chrome.
