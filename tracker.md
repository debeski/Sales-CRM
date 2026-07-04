# Project Tracker (switch-pos) [Max 100 lines total]

## Part 1: Project Related

### Current Verified Snapshot:
Django POS/ERP on django-lux 1.2.14. Apps: finance, catalog, sales, common. USD-base pricing → LYD via global ExchangeRate. Postgres/Redis/Celery(+beat via `-B`) via compose. Edge = Caddy w/ automatic HTTPS, per-hostname: erp.switchlibya.ly → ERP; apex+www → static ./portfolio. v0.1.4 in progress (untagged, composer-updater pipeline); v0.1.3 tagged+published. Migrations clean; 29 tests pass. compose config validates (prod+dev).

### Current Project Adopted Standards:
- Scoped models via dlux ScopedModel; list pages via common.ScopedListView + dlux modal_manager.
- Money frozen per-invoice (exchange_rate + unit_price_lyd). finance is dependency root.
- Filters use dlux setup_filter_helper; forms use dlux set_field_attrs.

### Adopted Standards' rules and policies:
- Never delete: move to ./.xpose/ preserving path.
- CSP active + network isolation (v0.1.4 3+1 model): `internal` is `internal:true`; egress bridge = smtp-relay/dlux-updater/celery/composer-updater; `frontend`=Caddy ingress; `docker_proxy` (internal) = composer-updater↔docker-socket-proxy. web is cache-only for scraped data.
- External data (rate scrapes) runs in celery; web reads Redis cache. Network changes need `./start.sh -d` (recreate), not `-r`.

### Cross-Cutting Audits if any:
Audit done 2026-07-02: barcode already present; migrations clean; no scraping deps yet.

### Current Project's Unsolved Known Bugs:
- None open. (Modal table-in-form + unlabeled filters fixed in v0.1.2.)

### Incomplete Tasks:
- **Priority 1:**
  - [ ] Optional: inject per-list Add button into the filter bar (config "buttons") vs current separate top-right button.
  - [ ] Browser smoke-test modal edit/delete (row actions) — combobox verified via test client.
- **Completed Recently:**
  - [x] (v0.1.4) Portfolio toggles: `portfolio/index.html` real theme (data-theme+localStorage sl_theme, pre-paint no-FOUC, tracks OS until chosen) + language (ع/EN, data-i18n dict 50 keys EN/AR, flips lang/dir RTL) switches; removed the lone hard-coded Arabic tagline; polish (scroll-margin, focus rings, reduced-motion). Stays a host bind-mount (not baked) per user. Keys verified 50/50 both langs.
  - [x] (v0.1.4) Composer-updater pipeline (mirror of project-decrees, Caddy-adapted): Dockerfile `ARG DLUX_BAKED_VERSION`+`LABEL org.switchlibya.dlux_baked_version`; release.yml resolves ver from `django-lux[updater]==` in requirements.txt → build-args on both build steps. New services `composer-updater` (debeski/composer:1.1.5 watch) + `docker-socket-proxy` (tecnativa, least-priv). Networks consolidated `sales_net`/`sales_internal`/`dlux_update_egress` → `frontend`/`egress`/`internal`/`docker_proxy` (celery→egress+internal, caddy→frontend+internal). compose.dev: +dlux mount on smtp-relay. settings.py: `dlux_settings` on own import line (noqa). CHANGELOG v0.1.4 + VERSION 0.1.4 + OPERATIONS.md topology+composer section. compose config prod+dev OK.
  - [x] (v0.1.3) Edge split by hostname (Caddy): `(erp_app)` snippet imported by `{$CADDY_ERP_ADDRESS}` (ERP, erp.subdomain) + new `{$CADDY_SITE_ADDRESS}` block file_servers `./portfolio` (apex+www static landing). BREAKING .env: `NGINX_SERVER_NAME`→`CADDY_ERP_ADDRESS`; `CADDY_SITE_ADDRESS`=portfolio host(s). Defaults keep dev (`:80` catch-all, portfolio→http://portfolio.localhost no-ACME). `BASE_URL`/`ALLOWED_URLS`=https://erp.switchlibya.ly, `ALLOWED_HOSTS`+=erp. New `portfolio/index.html` (self-contained responsive landing). Needs DNS A records for @/www (only erp existed). `caddy validate`+`docker compose config` pass. OPERATIONS.md rewritten.
  - [x] (v0.1.3) Catalog price consistency: `Product.save()` persists derived `price_usd` (detail no longer shows 0.0); `catalog/js/price_sync.js` live-syncs cost/markup/USD/LYD in the modal (loaded via new `ScopedListView.extra_scripts`); LYD stays LIVE (override blank unless typed — shown as placeholder). Detail gets computed "Selling Price (LYD)" row via `get_modal_context` + project override of `dlux/helpers/dynamic_modal_detail.html`. `get_{unit,service_type,movement_type}_display` overridden → translated choice in detail. New `common.forms.translate_help_text` (help_<model>_<field> keys) called from all ModelForms; added catalog/finance help_* + `label_*_selling_price_lyd` AR/EN keys. +4 tests.
  - [x] (v0.1.3) SSL/edge: replaced nginx+certbot with a `caddy` service + `Caddyfile` (automatic Let's Encrypt HTTPS, zero one-off commands — fits composer `./start.sh`). Old nginx deadlocked (443 needed certs that didn't exist yet → port 80 ACME never served). Ported all nginx rules (static cache, media + dlux_backups 404, pgadmin subpath, maintenance-flag 503, health). New `caddy_data`/`caddy_config` volumes; fixed `${NGINX_PORT:-443}` port-collision bug (→ `HTTP_PORT`/`HTTPS_PORT`). dev override → caddy on :80/host 90. `caddy validate` passed. Old template → `.xpose/`. CHANGELOG v0.1.3 + VERSION 0.1.3 + OPERATIONS.md deploy section. Live-deploy fix: dropped the ACME `email` directive — the `webmaster@localhost` default made LE reject issuance (`invalidContact`), and an empty `email`/`tls` value won't parse; Caddy auto-renews without a contact (notices opt-in via `{ email … }`).
  - [x] Fix sidebar: moved invoice_list /sales/ -> /sales/invoices/ (+ /sales/ redirect to dashboard) so dlux prefix-match doesn't highlight Invoices on every sales page.
  - [x] Payment deposit = search-and-add combobox (find-or-create batch by reference); deposit amount auto-sums linked payments (recalc on Payment save/delete); CashDepositForm locks amount when it has payments. Optional. 27 tests. Product decision: deposits stay optional (mixed cash flow); NO customer-accounts for now (per-invoice).
  - [x] perm_<codename> AR/EN keys (catalog/finance/sales) so group-manager permission labels translate the model name (dlux only localizes the verb). Model headers already translated. Verified: 0 English AR perm labels.
  - [x] Fix Django 6.0 format_html crash in ProductTable.render_stock_qty (untracked product "—"); +regression test. 23 tests pass.
  - [x] seed_demo mgmt command (rates/catalog+stock/customers/invoices all statuses/payments/deposits); idempotent + --reset. 22 tests pass.
  - [x] Form-only modals (scoped_modal_manager/delete + scoped_crud.js + refresh_parent).
  - [x] Dashboard custom + CBL official + EAN black-market rates (scrape, celery egress, beat + worker_ready warm). Verified live: CBL 6.4117, EAN 8.50↓.
  - [x] Customer search-and-add combobox + phone/address autofill + persist. Verified via test client: create-new, reuse-existing (no dup), snapshot backfill. +3 tests.
  - [x] Filters: per-FilterSet advanced_config via advanced_filter_helper. KEY FIX: render with {% crispy filter.form %} TAG (the |crispy filter ignores form.helper). Verified pages render collapse+toggle+autosubmit.
  - [x] Dropdown OPTION labels translated via dlux translate_choices (common.forms.translate_choice_fields) on filters+modal forms; added choice_* AR/EN keys. Fixed django_filters placeholder rendering (write widget.choices, not field.choices). Verified live render.
  - [x] Barcode column in ProductTable (field already existed).
  - [x] CHANGELOG v0.1.2 + VERSION bump + docs/OPERATIONS update.

### One-line info about last verified Tests:
29 tests pass (config.settings_dev_sqlite); +catalog pricing-consistency & help-text tests; detail modal verified live via test client (LYD row, AR unit علبة, USD 130,00); system check clean.

### One-line info about last time edited Docs:
docs/OPERATIONS.md — networking rewritten to 3+1 topology table + new "Composer-as-updater" section (version gate, socket-proxy) (v0.1.4).

## Part 2: Global

### Global Standard Helpers, Shortcuts, Info, etc.:
- venv python: /Users/debeski/Desktop/depy/project-switch-pos/.venv/bin/python
- dev settings: config.settings_dev_sqlite
- dlux modal view: DynamicModalManagerView (show_table/show_form attrs); URL name `modal_manager`.
- dlux filter helpers: setup_filter_helper / advanced_filter_helper (utils/crud.py).

### Global Rulesets:
- Update CHANGELOG + docs same turn as feature/config changes. Tag-driven releases.

### Agent Handoff Rules:
- Confirm outward-facing / multi-file changes before sweeping edits.

### References and Links:
- CBL rates: https://cbl.gov.ly/currency-exchange-rates/ (static table; USD avg ~6.41).
