# Project Tracker (switch-pos) [Max 100 lines total]

## Part 1: Project Related

### Current Verified Snapshot:
Django POS/ERP on django-lux 1.3.2. Apps: finance, catalog, sales, common. USD-base pricing → LYD via global ExchangeRate. Postgres/Redis/Celery(+beat via `-B`) via compose. Edge = Caddy w/ automatic HTTPS, per-hostname: erp.switchlibya.ly → ERP; apex+www → static ./portfolio. v0.2.2 (images, camera, form layouts, stock-take, fiscal-year report, invoice attachment, exact COGS) merged to main (untagged); v0.2.1 tagged+published. Migrations squashed (catalog/0003, sales/0004); 69 tests pass. compose config validates (prod+dev).

### Current Project Adopted Standards:
- Scoped models via dlux ScopedModel; list pages via common.ScopedListView + dlux modal_manager.
- Money frozen per-invoice (exchange_rate + unit_price_lyd). finance is dependency root.
- Filters use dlux setup_filter_helper; forms use dlux set_field_attrs.
- Row-level visibility (v0.2.0): owned models set `OWNER_FIELDS` + `view_all_<model>` perm; `common.access.apply_ownership` at READ choke points only (NOT the manager — keeps child recalcs whole). Roles: superuser / Sales Manager / Sales Representative / Delivery Courier via `seed_roles`.

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
  - [x] (v0.2.2) Fiscal-year financial report + invoice attachment. Report `/sales/financial/` (perm `view_financial_report`, NOT row-scoped — whole-store P&L): revenue/COGS-est/gross-profit/margin/cash (period) + receivables/inventory-value (current snapshot) + revenue-by-month; FY=calendar year, year picker. `build_financial_report()` in sales/reports.py. COGS EXACT: `InvoiceItem.unit_cost_usd` frozen at sale (editor _apply_item_price + save() fallback); report COGS = qty×frozen cost×invoice frozen rate, Coalesce→current cost for legacy lines. Dashboard Financial button; seed_roles Manager granted. Invoice `attachment` FileField (upload_to invoices/) via dlux archive widget (show_scan=True, accept image+pdf) in header grid; editor form +enctype multipart + pass request.FILES; detail paperclip link. All 3 changes squashed into **Migration sales/0004** (financials: view_financial_report perm + attachment + unit_cost_usd). +6 tests. On branch feat/catalog-images.
  - [x] (v0.2.2) Stock take + inventory valuation (the "annual inventory"): new `catalog.StockTake`+`StockTakeLine`. Full-page count sheet snapshots system_qty per active tracked product + counted input (open status). Detail = variance report (system/counted/signed variance/LYD value); `apply_stocktake` perm → Apply posts 1 ADJUST StockMovement per real discrepancy (sets stock_qty=counted via existing signed ledger), locks applied (re-apply raises). Inventory Valuation report `/catalog/valuation/` = Σ(stock×cost) USD+LYD, `view_inventory_valuation` perm. StockTakeList (+New/Valuation buttons via new `list_actions` block in scoped_list.html), Table/Filter/routes/EN-AR. NOT row-scoped (mgmt, perm-gated); seed_roles Manager granted. Migration catalog/0003. +7 tests. Views tested via RequestFactory+FallbackStorage. On branch feat/catalog-images.
  - [x] (v0.2.2) Catalog images: optional `image` ImageField on Product+Service (upload_to catalog/products|services/). Form field uses **dlux archive file widget** (`_build_archive_file_widget`, drag-drop+preview) not plain input — `accept=image/*` preserved (phone camera/gallery); modal-safe (file_field.js global + MutationObserver). 38px thumbnail in ProductTable/ServiceTable (mark_safe placeholder — Django6 format_html needs args), larger thumb in detail modal via new `is_html` flag on `extra_detail_fields` override + shared `_image_detail_row()`. Verified modal uploads: dlux modal submits FormData multipart + manager POST passes `request.FILES`. Pillow pinned. Media served by Caddy (prod) + Django static() under DEBUG (dev); CSP img-src SELF. +5 tests. Migration catalog/0003. On branch feat/catalog-images.
  - [x] (v0.2.2) Multi-column modal forms: KEY FINDING — the `DynamicModalManagerView` (our scoped_modal_manager) renders `{% crispy form %}` with NO helper/layout → fields stacked 1/row (the 2-col chunk code is in dlux's UNUSED section-manager view, not this path; nothing "overwrites" it). New `common.forms.build_grid_helper(form, rows)` sets form.helper + crispy Layout (Row/Column, 2–3 across, textareas/image full-width); no submit input so dlux icon buttons stay; drops absent perm-gated fields + appends unlisted ones full-width (never loses a field). Applied to modal forms (catalog Category/Product/Service/StockMovement, sales Customer/Delivery, finance ExchangeRate/CashDeposit) + full-page InvoiceForm header (switched invoice_form.html `{{ form|crispy }}` filter→`{% crispy form %}` tag; filter drops form.helper — the [[dlux-crispy-tag-vs-filter]] gotcha; items formset untouched; hidden customer FK emitted as bare input). Also added `help_product_track_stock` EN/AR (Track Stock toggle description). +4 render/help tests. 55 pass. NEEDS a browser eyeball (visual polish/RTL not testable).
  - [x] (v0.2.0) Per-employee row-level visibility: new `common/access.py` (`apply_ownership` reads model `OWNER_FIELDS` + `view_all_<model>` perm; superuser/view_all bypass; shared models untouched). Applied at READ choke points (ScopedListView, invoice detail/print/editor/issue/cancel/pay `_visible_invoices`, build_sales_report, private-customer datalist/`_sync_customer`) — NOT the manager (keeps `invoice.payments.all()` recalcs whole). Invoice `salesperson` FK (defaults to creator; manager-only picker via `assign_salesperson`). Owned: Invoice/Customer/Payment/finance.CashDeposit. New `sales.Delivery` model (assigned_to courier, status lifecycle, invoice snapshot) + List/Table/Filter/Form/route/EN-AR strings. Modal-manager hole closed via `install_modal_ownership_patch` wrapping dlux `_scope_filtered_modal_queryset` (installed on first request_started to dodge init-DB warning). Dashboard gated+row-scoped (courier sees deliveries, not sales — fixed prior ungated leak). `seed_roles` → 3 groups (Manager/Rep/Courier). +15 tests (test_visibility.py), 46 pass. Migrations sales/0003 + finance/0002. Docs: PERMISSIONS.md rewritten + BUSINESS_RULES visibility/delivery sections. On branch feat/per-employee-visibility (uncommitted).
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
69 tests pass (config.settings_dev_sqlite); +6 sales/tests/test_financial.py (fiscal window, report figures, whole-store not row-scoped, view perm+year, COGS uses FROZEN line cost when product cost changes) +1 invoice attachment (dlux widget, multipart, saves); +7 catalog/tests/test_stocktake.py (auto-number, variance, apply posts adjustments/sets stock/skips untracked+exact, re-apply raises, variance value, create snapshots lines, valuation totals); +images/grid/invoice-header tests; makemigrations --check clean; system check clean.

### One-line info about last time edited Docs:
docs/BUSINESS_RULES.md — added "Fiscal year & financial report" + "Invoice attachment" sections; PERMISSIONS.md += view_financial_report (v0.2.2).

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
