# Deploy marketing site to Hostinger (VPS) with GitHub Actions

This repository can publish the **`website/`** folder to your Hostinger VPS on every push to `main` (when `website/` changes). The existing [GitHub Pages workflow](../.github/workflows/deploy.yml) is unchanged and still deploys the full repo to Pages.

## 1. Prepare the VPS (one-time)

SSH into the VPS from Hostinger hPanel (IP, port, root or sudo user).

### Web root

Create a directory for the site (example):

```bash
sudo mkdir -p /var/www/sanket/html
sudo chown -R "$USER:$USER" /var/www/sanket/html
```

Use this path as **`DEPLOY_PATH`** in GitHub (no trailing slash required).

### Nginx (example)

```bash
sudo apt update && sudo apt install -y nginx
```

Create `/etc/nginx/sites-available/sanket-website`:

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name example.com www.example.com;

    root /var/www/sanket/html;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}
```

Enable and reload:

```bash
sudo ln -sf /etc/nginx/sites-available/sanket-website /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

After DNS works, add HTTPS (Hostinger panel or Certbot).

### Deploy user and SSH key

Either use your normal SSH user (if it can write to `DEPLOY_PATH`) or a dedicated user:

```bash
sudo adduser --disabled-password deploy
sudo chown -R deploy:deploy /var/www/sanket/html
```

On your PC, generate a key **only for GitHub Actions** (do not commit this file):

```bash
ssh-keygen -t ed25519 -C "github-actions-sanket-website" -f deploy_key -N ""
```

On the VPS, append the **public** key to the deploy user’s `~/.ssh/authorized_keys`.

Test from your PC:

```bash
ssh -i deploy_key -p 22 deploy@YOUR_VPS_IP "echo ok"
```

## 2. GitHub repository secrets

In the repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Example | Notes |
|--------|---------|--------|
| `SSH_HOST` | `123.45.67.89` | VPS IP or hostname |
| `SSH_USER` | `deploy` | User that owns `DEPLOY_PATH` |
| `SSH_PRIVATE_KEY` | contents of `deploy_key` | Full file including `-----BEGIN...` |
| `DEPLOY_PATH` | `/var/www/sanket/html` | Document root on the server |
| `SSH_PORT` | `22` | Optional; defaults to 22 if omitted |

## 3. Run the workflow

- Push a change under `website/`, or  
- **Actions → Deploy website to Hostinger → Run workflow**

The job rsyncs `website/` to `DEPLOY_PATH` with `--delete` (removes files on the server that were removed from the repo).

## 4. GoDaddy DNS

In GoDaddy → your domain → **DNS**:

| Type | Name | Value |
|------|------|--------|
| **A** | `@` | Your Hostinger VPS IP |
| **A** or **CNAME** | `www` | Same IP, or CNAME to apex |

Remove old A/CNAME records that conflict. Propagation can take up to 24–48 hours.

In Hostinger, attach the domain to the VPS if required and enable SSL once DNS resolves.

## 5. Notes about links in `website/`

- PTT / Transcribe demo links still point at **GitHub Pages** (`vibhvesh.github.io/sanketptt/...`). That is fine while Pages stays active.
- Links like `../aakashvani/` only work if that app is also hosted on the same domain or you change them to absolute URLs.

After your custom domain is live, you can update nav links in `website/index.html` if you want everything under one hostname.

## 6. Troubleshooting

| Symptom | Check |
|---------|--------|
| Workflow fails “Missing repository secret” | Add all required secrets in GitHub |
| Permission denied (rsync) | `chown`/`chmod` on `DEPLOY_PATH`; correct `SSH_USER` |
| 502 / connection refused | Nginx running; firewall allows 80/443 |
| Site shows old content | Hard refresh; confirm workflow succeeded |
| `../aakashvani/` 404 on custom domain | Expected unless you deploy that folder or change links |