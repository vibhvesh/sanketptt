# Sanket product website

Standalone public-facing website for the Sanket product family.

## Local preview

Open `index.html` in a browser. It is a self-contained static page (HTML, CSS and JavaScript) and has no build dependencies.

## Public site

The marketing page is served at https://sanketptt.com/. Push-to-talk, Transcribe, DMR, guides and installers are published under the same host (`/?ch=`, `/transcribe/`, `/dmr/`, `/docs/`, `/pi/install.sh`). This shorter layout is on the `dev` branch and is not deployed by the Hostinger workflow until that branch is merged to `main`.

## Hostinger (custom domain)

Hostinger deploy (GitHub Actions) syncs **`website/`** plus **`aakashvani/`** on push to `main`. See [docs/DEPLOY_HOSTINGER.md](../docs/DEPLOY_HOSTINGER.md).

`website/` is the Hostinger document root. It includes the marketing page and copies of the PTT app (`radio/`), Transcribe, DMR, guides, Pi installer and Android APKs so those paths resolve on https://sanketptt.com.

## Product guide screenshots

Guide images are served from `/docs/img/` on the same host.

## Notes

- Dashboard signal graphs in the product previews are illustrative. The homepage relay, presence and radio directory are live and fall back to an explicit offline or built-in-station state when a service is unavailable.
- Contact form opens a prefilled email draft to Akshat Singh; it does not submit to a backend.
- Public contact: Akshat Singh, akshatsingh@canberravision.com, akshat@sanketptt.com, +91 99982 99023, Canberra Vision, 713 Samanvay Silver, Akota, Vadodara, Gujarat, India.
- Sanket SDR does not publish a price. The card asks for a meeting and does not describe specific capabilities.
