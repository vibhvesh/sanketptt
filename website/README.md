# Sanket product website

Standalone public-facing website for the Sanket product family.

## Local preview

Open `index.html` in a browser. It is a self-contained static page (HTML, CSS and JavaScript) and has no build dependencies.

## GitHub Pages

The site is published at:

https://vibhvesh.github.io/sanketptt/website/

The existing Sanket PTT root app, Transcribe app and Pi service are not modified by this website folder.

## Product guide screenshots

The page references existing guide screenshots from `docs/img/` in this repository using raw GitHub URLs.

## Internal lead finder

`/leads/` is an unlisted sales page (noindex, not in the site menu). It calls the Render API at https://sanket-leads.onrender.com. Setup is in [`../leads/README.md`](../leads/README.md).

## Notes

- Dashboard activity, messages, signal graphs and counts are illustrative sample data, not live system telemetry.
- Contact form opens a prefilled email draft; it does not submit to a backend.
- Update the public contact email/address details after confirming the preferred business contact information.
- SDR content describes receive-only spectrum monitoring; use only lawful public or authorised frequencies.
