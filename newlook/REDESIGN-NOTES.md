# Sanket New Look — Design and QA Notes

Preview: https://vibhvesh.github.io/sanketptt/newlook/

## Scope preserved
- The redesign is a separate copy under `/newlook/`.
- Existing homepage sections, product descriptions, IDs, contact/pricing content, radio directory data, and live application destinations are retained.
- The separate live demo page is copied to `/newlook/demo.html`.
- Existing brand mark and four product mockup SVGs are copied into the preview.
- The current `/website/` site and production PTT/Transcribe/DMR applications are not modified by this redesign.

## Design audit observations
These are design and maintainability observations from inspecting the source, not claims that every item was a runtime failure.

1. The top navigation had multiple links and prominent actions competing for attention, especially at tablet widths.
2. The main page and live demo used different visual languages; the demo had a warm brown header and border treatment that did not match the main site.
3. The page had accumulated many incremental CSS overrides, making the final visual system difficult to reason about.
4. Cards, image frames, forms, dropdowns, and buttons did not share one consistent radius, elevation, focus, and hover treatment.
5. Mobile navigation needed stronger spacing, clearer action hierarchy, and larger tap targets.
6. The page contained many product sections and live widgets; the visual hierarchy needed calmer section spacing and clearer surfaces.

## Changes implemented
- Added a separate premium light-surface design system with deep navy, teal signal accents, and restrained orange CTAs.
- Standardized card, panel, image, input, select, dropdown, and button treatments.
- Added soft shadows, rounded surfaces, hover feedback, and short transitions.
- Improved sticky navigation styling and mobile menu spacing; preserved the three direct application links.
- Restyled the standalone PTT + Transcribe demo page to match the new site.
- Added reduced-motion handling and visible keyboard focus styling.
- Preserved the existing PTT/Transcribe iframe destinations and channel-sharing behavior.

## Static checks performed
- Homepage: 11 inline scripts parsed successfully with JavaScript syntax checks.
- Demo page: 1 inline script parsed successfully.
- No duplicate HTML IDs found in either page.
- No missing same-page fragment targets found.
- CSS brace balance checked for all style blocks.
- Local preview assets present: brand SVG and four product mockup SVGs.
- Radio directory JSON parsed successfully.
- Original `website/index.html` blob remained unchanged during preview creation.

## Remaining validation
- GitHub Pages publication and live browser rendering must finish before visual acceptance.
- A real device/browser pass is still required for menu interaction, language picker behavior, iframe audio permissions, layout at narrow widths, and external destination availability.
- The web preview checker could not load the new URL at the time of this audit, so this report does not claim a completed live visual test.
