# Redesign strategy

## Audience

Operations leads, security and logistics managers, event crews, and public-sector buyers who need a radio that works in a browser. They compare Sanket with global push-to-talk apps and with buying their own server. Developers are a second audience: they need the real clients and the link book, not a brochure.

## Problems found

The preview already had the right facts, but the pages felt like a template stacked on a template. Pricing, the live radio, the product list, and the jobs people hire Sanket for were all on the homepage. Photography was small and late. The type was one family at one weight, so nothing felt like a headline. Industry pages repeated the same card grid with no picture of the work.

## Design system

Two families: Fraunces for headlines, Manrope for interface text, both from Google Fonts with `display=swap`. The palette keeps a near-black ground and a burnished amber, softened so it reads as metal rather than a warning light. Light mode uses warm paper. Spacing steps are 8, 16, 24, 40, and 72. Buttons are pills. Icons stay inline SVG. Sections fade in on scroll unless the visitor prefers reduced motion.

## Page map

- `/` hero, facts, product story, comparison, how it works, gallery, live radio, contact.
- `/demo/` the auto-joining Virtual radio, plus free channels, Try, and the console.
- `/pricing/` Cloud, local, enterprise, dedicated, आकाशवाणी, SDR, SanketVaani. No add-on rows.
- `/applications/` every working app.
- `/use-cases/` and `/industries/*` the jobs, with the photographs.
- PTT 2, radios, transcribe, and the other clients stay their own apps. The free Virtual join is unchanged.

## What we will not invent

No customer counts, no quotes, no new prices. The only numbers on the site are the ones already published: ₹450 per line, the volume terms, the hardware prices, about one second to talk, 4G and Wi-Fi, and Gujarati, Hindi, and English.
