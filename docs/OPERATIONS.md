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
5. **Sales → New Invoice**: pick a customer or type a walk-in name, add product /
   service lines (prices auto-fill), Save Draft → **Issue** → record payments.
   **Print / Export** produces a clean printable invoice (Save as PDF from the
   browser dialog).

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

## CI / Docker image

`.github/workflows/docker-publish.yml` builds the `Dockerfile` and pushes
`debeski/sales:latest` (and `debeski/sales:<git-sha>`) to Docker Hub on push to
`main`/`master` or via manual **Run workflow**.

Required repository **Secrets** (Settings → Secrets and variables → Actions → *Secrets* tab):

| Secret | Value |
|--------|-------|
| `DOCKERHUB_USERNAME` | Docker Hub username (`debeski`) |
| `DOCKERHUB_TOKEN` | Docker Hub access token (Read/Write scope) |

> The token must be a **Secret**, not a *Variable* — Variables are printed in build logs.
> To deploy the published image instead of building locally, set `WEB_IMAGE=debeski/sales:latest`
> for `compose.yml` (the prod compose already reads `${WEB_IMAGE:-switch_pos:latest}`).

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
