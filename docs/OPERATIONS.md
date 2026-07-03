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
stack (db, redis, nginx, web, celery, smtp-relay, pgadmin, db-backup) and runs the
`migrator` post-start task. In DEV mode the app is served at **http://localhost:90**.

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
   brand the printed invoice).
2. **Finance → Exchange Rates → Add**: enter the current black-market USD→LYD rate.
   The dashboard warns until this is done.
3. **Catalog → Categories / Products / Services**: add what you sell. For products,
   enter `cost_usd` + `markup_percent` (or a direct `price_usd`); add a *Stock In*
   movement to set initial quantity.
4. Create staff users and add them to **Sales Staff** (`seed_roles` made the group).
5. **Sales → New Invoice**: type or pick a customer in the single search box —
   existing customers autofill phone/address, and a new name is saved as a
   customer for next time. Add product / service lines (prices auto-fill), Save
   Draft → **Issue** → record payments. **Print / Export** produces a clean
   printable invoice (Save as PDF from the browser dialog).

## Key URLs

| Path | Page |
|------|------|
| `/sales/dashboard/` | Dashboard (set as Home URL in System Settings) |
| `/sales/` | Invoices |
| `/sales/new/` | New invoice editor |
| `/catalog/` | Products & stock |
| `/catalog/services/` | Services |
| `/finance/rates/` | Exchange rates |
| `/finance/deposits/` | Cash deposits |
| `/sales/report/` | Sales report (XLSX export from here; owner-only) |

## Scheduled tasks (Celery Beat)

The `celery` service runs both a worker and Beat (see `compose.yml`). Scheduled
jobs are declared in `config/celery.py` under `app.conf.beat_schedule`:

| Task | Schedule | Purpose |
|------|----------|---------|
| `finance.tasks.refresh_market_rates` | every 3h | Scrapes two USD→LYD reference rates and caches them (**no expiry** — replaced only by a later successful scrape): the **official** rate from [cbl.gov.ly](https://cbl.gov.ly/currency-exchange-rates/) (`finance:cbl_official_usd_rate`) and the **black-market** rate + trend from [eanlibya.com](https://www.eanlibya.com/exchangerate/) (`finance:ean_black_market_usd_rate`). |

The **dashboard** shows both reference rates next to the in-house *custom* rate.
Each scrape is server-side (the CSP `connect-src` blocks a browser cross-origin
fetch) and independent — if one site is down its last cached value is kept while
the other still updates. This is display-only — invoices always freeze the custom
`ExchangeRate`, never a scraped rate.

**Networking**: `web` and the rest of the stack sit on the isolated
`switch_pos_internal` network (`internal: true`, no egress). The scrape therefore
runs in the **celery** service, which is additionally attached to the egress bridge
`switch_pos_net`; the web tier reads the scraped rates **cache-only** from Redis
(it never makes an outbound call). A `worker_ready` signal warms the cache on
celery boot so values appear without waiting for the first 3-hourly Beat run.
Applying the network change needs a recreate (`./start.sh -d`), not just a restart.

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

Set **System Settings → Home URL** to `/sales/dashboard/` to make the dashboard the landing page.

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
