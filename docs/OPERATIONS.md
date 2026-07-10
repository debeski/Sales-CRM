# Switch POS — Operations & Setup

## Production-style run (Postgres + Redis, via Docker)

The dlux scaffold ships Docker assets. Bring up the stack:

```bash
./start.sh -d                                  # composer orchestrator (DEV mode → app on http://localhost:90)
# or directly:
docker compose --env-file .secrets/.env -f compose.yml -f compose.dev.yml up
```

`./start.sh -d` runs the `debeski/composer` image, which decrypts `.secrets`,
builds the `web`/`celery`/`smtp-relay` images from the `Dockerfile`, starts the
stack (db, redis, caddy, web, celery, smtp-relay, pgadmin, db-backup) and runs the
`migrator` post-start task. In DEV mode the app is served at **http://localhost:90**.

## Production deploy with a domain + automatic HTTPS

The edge is a **Caddy** reverse proxy (`Caddyfile`, `caddy` service). Caddy
obtains and renews Let's Encrypt certificates automatically on boot — there is
no certbot step, no bootstrap command, and no manual reload. A plain
`./start.sh` is the entire TLS workflow.

Caddy serves **two independent sites, routed by hostname** (this is an edge
concern, not a Django one — Django never sees the apex/www requests):

| Hostname(s)                              | Served by            | Env var             |
|------------------------------------------|----------------------|---------------------|
| `erp.switchlibya.ly`                     | the Django ERP (proxy to `web:8000`) | `CADDY_ERP_ADDRESS` |
| `switchlibya.ly` `www.switchlibya.ly`    | static portfolio (`./portfolio`, mounted read-only at `/srv/portfolio`) | `CADDY_SITE_ADDRESS` |

Each hostname gets its **own** auto-provisioned Let's Encrypt cert. The ERP stays
entirely on the `erp.` subdomain; `CSRF_COOKIE_DOMAIN`/`SESSION_COOKIE_DOMAIN`
follow `BASE_URL`'s hostname, so ERP cookies are scoped to `erp.switchlibya.ly`.

1. Point **A/AAAA records** at the VPS public IP for **all three** names:
   `erp` (the ERP), `@`/apex, and `www` (the portfolio). Open **inbound TCP 80
   and 443** on the host firewall — Caddy needs both for the ACME challenge and
   to serve traffic. (A name that doesn't resolve yet just fails its own cert and
   retries; it does not affect the other site.)
2. In `.secrets/.env` set:
   ```ini
   CADDY_ERP_ADDRESS=erp.switchlibya.ly                    # the ERP subdomain
   CADDY_SITE_ADDRESS=switchlibya.ly www.switchlibya.ly    # portfolio host(s)
   ALLOWED_HOSTS=erp.switchlibya.ly,web,localhost,127.0.0.1
   ALLOWED_URLS=https://erp.switchlibya.ly
   BASE_URL=https://erp.switchlibya.ly
   ```
   > **Migrating from a single-domain deploy:** the ERP host variable changed
   > from `NGINX_SERVER_NAME` to **`CADDY_ERP_ADDRESS`**. Update your `.env` or
   > the ERP block falls back to `localhost` and won't get its cert.

   No ACME email is required — Caddy issues and auto-renews certs without one. To
   receive Let's Encrypt expiry notices, add a real address to the `Caddyfile`
   global block (`{ email you@your-domain.tld }`); the domain must contain a dot.
3. Bring the stack up in production (no `-d`):
   ```bash
   ./start.sh
   ```
   On first boot Caddy issues a cert per hostname (watch `docker compose logs
   caddy`); each site is live on HTTPS with HTTP→HTTPS redirect. Certs persist in
   the `caddy_data` volume and auto-renew.

Edit the public landing at **`./portfolio/index.html`** (a self-contained static
page — no rebuild needed; `docker compose restart caddy` picks up changes, or
they serve immediately since the dir is mounted). Override the published ports
with `HTTP_PORT` / `HTTPS_PORT` (default `80`/`443`) and the upload cap with
`CADDY_MAX_SIZE` (default `10MB`) if needed.

Then migrate, seed roles, and create the owner:

```bash
python manage.py migrate
python manage.py seed_roles
python manage.py createsuperuser
```

On first visit the system runs the DjangoLux **setup wizard** (system name, logo,
language, theme). Health endpoint: `/health/`.

## First-run checklist

1. Complete the setup wizard (set the Arabic/English system name + logo — these
   brand the printed sales invoice, payment receipt, and purchase invoice).
2. **Finance → Exchange Rates → Add**: enter the current black-market USD→LYD rate.
   The Workspace dashboard warns until this is done.
3. **Catalog → Categories / Products / Services**: add what you sell. For products,
   enter `cost_usd` + `markup_percent` (or a direct `price_usd`). Product variants
   (`color` and free-form `size` / spec) are descriptive only; set them during
   Opening Stock or Purchase Invoice intake, then review them from product
   list/detail screens.
   - **Bulk shortcut for first setup:** **Catalog → Stock Movements → Opening
     Stock (bulk)** loads everything already on the shelf in one grid — one row
     per item, each a new or existing product, with the quantity currently in
     storage. Rows can also set optional color and size/spec. Submit to create
     the items and post the opening stock in one go (the result appears as Stock
     In movements). It can only be applied once;
     afterward the button becomes a view-only Opening Stock record. See
     BUSINESS_RULES → *Opening stock*.
   - **Normal stock purchases after launch:** use **Catalog → Purchase Invoices**
     or **Catalog → Stock Movements → Add Stock**. This records supplier details,
     creates/reuses products, can set product color and size/spec at intake,
     accepts the supplier invoice scan/photo/PDF, and posts Stock In movements
     per line.
4. Create staff users and add them to one seeded role (`seed_roles` creates Sales
   Manager, Sales Representative, and Delivery Courier). For delivery people,
   technicians, or anyone carrying advances/loans/service payouts, create a
   **Finance → Staff Accounts** row so their ledger and confirmations have a home.
5. **Sales → New Invoice**: type or pick a customer in the single search box —
   existing customers autofill phone/address, and a new name is saved as a
   customer for next time. Add product / service lines (prices auto-fill); product
   lines also expose optional color and size/spec selectors when the selected
   product has those values. Save Draft → **Issue** → record payments.
   **Print / Export** produces a clean printable invoice (Save as PDF from the
   browser dialog).

## Key URLs

| Path | Page |
|------|------|
| `/workspace/` | Workspace dashboard (recommended Home URL in System Settings) |
| `/sales/dashboard/` | Sales Overview (sales-focused legacy dashboard) |
| `/sales/` | Invoices |
| `/sales/new/` | New invoice editor |
| `/catalog/` | Products & stock |
| `/catalog/services/` | Services |
| `/catalog/suppliers/` | Supplier list |
| `/catalog/purchase-invoices/` | Purchase invoices / inbound stock invoices |
| `/catalog/stock-movements/` | Stock ledger (+ Opening Stock / Add Stock buttons) |
| `/finance/rates/` | Exchange rates |
| `/finance/deposits/` | Cash deposits |
| `/finance/expenses/` | Operating expenses |
| `/finance/staff-accounts/` | Staff accounts / user credit |
| `/finance/staff-ledger/` | Staff ledger entries |
| `/sales/report/` | Sales report (XLSX export from here; owner-only) |
| `/sales/financial/` | Fiscal-year financial report with expenses/net profit |

## Scheduled tasks (Celery Beat)

The `celery` service runs both a worker and Beat (see `compose.yml`). Scheduled
jobs are declared in `config/celery.py` under `app.conf.beat_schedule`:

| Task | Schedule | Purpose |
|------|----------|---------|
| `finance.tasks.refresh_market_rates` | every 3h | Scrapes two USD→LYD reference rates and caches them (**no expiry** — replaced only by a later successful scrape): the **official** rate from [cbl.gov.ly](https://cbl.gov.ly/currency-exchange-rates/) (`finance:cbl_official_usd_rate`) and the **black-market** rate + trend from [eanlibya.com](https://www.eanlibya.com/exchangerate/) (`finance:ean_black_market_usd_rate`). |

The **Workspace dashboard** shows both reference rates next to the in-house
*custom* rate when the viewer has a rate, sales, or catalog permission.
Each scrape is server-side (the CSP `connect-src` blocks a browser cross-origin
fetch) and independent — if one site is down its last cached value is kept while
the other still updates. This is display-only — invoices always freeze the custom
`ExchangeRate`, never a scraped rate.

**Networking**: `web` and the rest of the stack sit on the isolated
`internal` network (`internal: true`, no egress). The scrape therefore
runs in the **celery** service, which is additionally attached to the egress bridge
`egress`; the web tier reads the scraped rates **cache-only** from Redis
(it never makes an outbound call). A `worker_ready` signal warms the cache on
celery boot so values appear without waiting for the first 3-hourly Beat run.
Applying the network change needs a recreate (`./start.sh -d`), not just a restart.

The full topology is a **3+1 network model**:

| Network | Type | Members | Purpose |
| --- | --- | --- | --- |
| `frontend` | bridge | `caddy` | Published ingress; bridge so the host reaches the app and Caddy reaches Let's Encrypt/ACME. |
| `egress` | bridge | `smtp-relay`, `dlux-updater`, `celery`, `composer-updater` | The only services with outbound internet (Gmail, PyPI, rate scrapes, Docker Hub). |
| `internal` | `internal: true` | `db`, `redis`, `web`, `caddy`, `celery`, `pgadmin`, `db-backup` | No-internet inter-service traffic. |
| `docker_proxy` | `internal: true` | `composer-updater`, `docker-socket-proxy` | Isolated Docker API path (see below). |

## Composer-as-updater (image-level updates)

The stack ships two services that let an operator (or dlux's in-app UI) roll the
deployment onto a newer published image without any host shell access:

- **`composer-updater`** (`debeski/composer:1.1.5`, `command: watch`) — a resident
  process that watches `/opt/dlux-runtime/state/image-update-request.json` on the
  shared `dlux_runtime` volume. On a request it runs `composer -uo` against the
  host daemon (pull → **version gate** → recreate → health → `post_start` migrator)
  and writes `deploy-status.json`. It talks to the daemon over TCP via the socket
  proxy (`DOCKER_HOST=tcp://docker-socket-proxy:2375`), never the raw socket. It is
  pinned (not `:latest`) so it won't recreate itself mid-update, and mounts the
  project at its host path (`${PWD}:${PWD}`) — **so the stack must be started from
  its root directory** for the `./media`/`./logs` bind mounts to resolve.
- **`docker-socket-proxy`** (tecnativa) — a least-privilege Docker API gateway that
  mounts `/var/run/docker.sock:ro` and exposes only the surface Compose needs
  (containers/images/networks/volumes/exec/POST/info/ping/version). Everything else
  (build, auth, secrets, swarm) stays denied.

**Version gate**: the image is built with `--build-arg DLUX_BAKED_VERSION=<ver>`
(CI reads the pinned `django-lux[updater]==` from `requirements.txt`) which is
stamped as `LABEL org.switchlibya.dlux_baked_version`. The updater
(`COMPOSER_VERSION_LABEL=org.switchlibya.dlux_baked_version`) refuses to recreate
onto an image whose baked version is older than the deployment's active runtime
version (`/opt/dlux-runtime/state/active.json`).

## CI / Docker image

Two workflows (tag-driven model — full details in [RELEASING.md](RELEASING.md)):

- **`.github/workflows/ci.yml`** — on push/PR to `main`: Django checks + tests
  (`config.settings_dev_sqlite`) and a Docker build + runtime smoke test (no push).
- **`.github/workflows/release.yml`** — on a `v*` tag: verifies `tag == VERSION`,
  smoke-tests, pushes multi-arch `debeski/sales:<ver>` + `:latest`, and creates a
  GitHub Release from the `CHANGELOG.md` section.

Required repository **Secrets**: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN` (token must
be a *Secret*, not a *Variable*). Deploy the published image with
`WEB_IMAGE=debeski/sales:latest ./start.sh -d`.

Set **System Settings → Home URL** to `/workspace/` to make the project-wide
Workspace dashboard the landing page. Keep `/sales/dashboard/` for the
sales-only overview when a sales-centric screen is useful.

## Local development without Postgres/Redis

A dev-only settings overlay runs everything on SQLite + local-memory cache:

```bash
python manage.py migrate       --settings=config.settings_dev_sqlite
python manage.py seed_roles     --settings=config.settings_dev_sqlite
python manage.py runserver      --settings=config.settings_dev_sqlite
```

`config/settings_dev_sqlite.py` is **not for production** — it only overrides the
database/cache so checks, migrations and smoke tests run on a laptop.

## Migrations

App migrations are committed under `finance/`, `catalog/`, `sales/` `migrations/`.
After changing a model: `python manage.py makemigrations && python manage.py migrate`.
Always update `docs/` and `CHANGELOG.md` in the same change.
