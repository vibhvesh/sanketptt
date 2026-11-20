# Sanket product website

Standalone public-facing website for the Sanket product family.

## Local preview

Open `index.html` in a browser. It is a self-contained static page (HTML, CSS and JavaScript) and has no build dependencies.

## GitHub Pages

The site is published at:

https://vibhvesh.github.io/sanketptt/website/

## Hostinger (custom domain)

Hostinger deploy (GitHub Actions) syncs **`website/`** plus **`aakashvani/`** on push to `main`. See [docs/DEPLOY_HOSTINGER.md](../docs/DEPLOY_HOSTINGER.md).

The existing Sanket PTT root app, Transcribe app and Pi service are not modified by this website folder.

## Product guide screenshots

The page references existing guide screenshots from `docs/img/` in this repository using raw GitHub URLs.

## Notes

- Dashboard signal graphs in the product previews are illustrative. The homepage relay, presence and radio directory are live and fall back to an explicit offline or built-in-station state when a service is unavailable.
- Contact form opens a prefilled email draft to Akshat Singh; it does not submit to a backend.
- Public contact: Akshat Singh, akshatsingh@canberravision.com, akshat@sanketptt.com, +91 99982 99023, Canberra Vision, 713 Samanvay Silver, Akota, Vadodara, Gujarat, India.
- The Sanket SDR product card is the defence surveillance offering and does not publish a price. Technical SDR previews on the page describe receive-only spectrum monitoring; use only lawful public or authorised frequencies.
