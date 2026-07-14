# Project Tracker (switch-pos) [Max 100 lines total]

## Part 1: Project Related

### Current Verified Snapshot:
Django POS/ERP on django-lux 1.4.4 (host venv symlinked to mounted source `/Users/debeski/Desktop/depy/pkg-django-lux/dlux`). Apps: finance, catalog, sales, common, public_catalog. Public `/` + `/shop/...` + `/contact/modal/`; staff workflow under `/staff/...` (+ `/staff/shop-builder/` catalog builder & `/staff/shop-builder/homepage/` homepage builder); Caddy only proxies/legacy-redirects. VERSION/CHANGELOG at v0.6.1 (unreleased; v0.6.0 is tagged). Current baseline: 171 pass. `public_catalog` unreleased migration is squashed to `0001`.

### Current Project Adopted Standards:
- Scoped models via dlux ScopedModel; list pages via common.ScopedListView + dlux modal_manager.
- Money frozen per-invoice (exchange_rate + unit_price_lyd). finance is dependency root.
- Stock variants are `ProductVariant(product,color,size,stock_qty)` buckets; `StockMovement.variant` updates product aggregate + variant qty; legacy no-variant lines use aggregate product stock.
- Filters use dlux setup_filter_helper; forms use dlux set_field_attrs.
- Row-level visibility (v0.2.0): owned models set `OWNER_FIELDS` + `view_all_<model>` perm; `common.access.apply_ownership` at READ choke points only (NOT the manager — keeps child recalcs whole). Roles: superuser / Sales Manager / Sales Representative / Delivery Courier via `seed_roles`.
- Public catalog is a curated `PublicCatalogListing` projection over Product/Service; current public write is idempotent `PublicContactMessage` only.

### Adopted Standards' rules and policies:
- Never delete: move to ./.xpose/ preserving path.
- CSP active + network isolation (v0.1.4 3+1 model): `internal` is `internal:true`; egress bridge = smtp-relay/dlux-updater/celery/composer-updater; `frontend`=Caddy ingress; `docker_proxy` (internal) = composer-updater↔docker-socket-proxy. web is cache-only for scraped data.
- External data (rate scrapes) runs in celery; web reads Redis cache. Network changes need `./start.sh -d` (recreate), not `-r`.
- Future public writes (reserve/purchase/checkout) require DB-backed idempotency keys; Redis/Celery may assist but cannot be the source of truth.

### Cross-Cutting Audits if any:
Audit done 2026-07-02: barcode already present; migrations clean; no scraping deps yet.

### Current Project's Unsolved Known Bugs:
- Live VM deployment drift observed 2026-07-12: `switchlibya.ly`/`www` still serve old static portfolio from Caddy while `erp.switchlibya.ly` proxies Django; current repo Caddy/Compose would proxy apex/www to Django and redirect `erp`, so VM is running old Caddy/Compose config or stale containers.
- Deployment `.secrets/.env` outbound email unset: `SMTP_RELAY_USER`/`SMTP_RELAY_PASSWORD` empty → smtp-relay can't auth to Gmail (email won't send until real creds added). Not foundation-related.
- Local dev sqlite drift only: leftover NOT NULL `sales_invoice.attachment` column (sqlite never dropped it post-v0.2.3) breaks `seed_demo` on that file. Schema from migrations is correct (tests green on fresh DB); recreate dev DB to clear.

### Incomplete Tasks:
- **Priority 1:**
  - [ ] Publish the first live listings via `/staff/shop-builder/`; set contact SMTP creds so contact emails send.
  - [ ] Design future reservation/purchase/checkout models with idempotency-key constraints before adding public POST endpoints.
  - [ ] Optional: inject per-list Add button into the filter bar (config "buttons") vs current separate top-right button.
  - [ ] Browser smoke-test modal edit/delete (row actions) — combobox verified via test client.
- **Completed Recently:**
  - [x] (v0.6.1) Homepage Builder Visual Studio: `switch_pos.public_homepage` normalized visual settings (`style_preset`, hero layout/height/focus, nav/card/density/background/motion, `accent_secondary`) + per-section `variant`; builder Style panel with icon controls/tablet preview; landing emits shell/hero/section hooks, visible preset directions, distinct spec/minimal cards, compact density, light sparse connected electrical grid, denser linework/wider diagonal bg variants, shop-disabled card link hiding, `?lang=` preview. Removed redundant homepage DLux Options tile; public catalog tile now only identity/contact/default disclosure settings. Assets `?v=20260714k`; browser smoke + 170 pass.
  - [x] (v0.5.1) Workspace reset removal: removed workspace dashboard Reset button/handler; DLux app prefs remain source of truth, and stale `localStorage` is cleared instead of rehydrating `switch_pos.workspace_dashboard.v1` after DLux Reset Defaults.
  - [x] (v0.5.1) Public Homepage Builder at `/staff/shop-builder/homepage/`: live-preview-iframe editor for the landing page (hero copy/CTA/background mode/overlay, reorderable+toggleable sections w/ per-section copy, Story block, accent colour). New `public_catalog/homepage.py` config in namespace `switch_pos.public_homepage`; `landing.html`/`PublicLandingView` fully config/section-driven (featured/categories/services/story/contact); accent → `--public-accent` var. `homepage_save` reuses `mutation_endpoint`+`sidebar_exclude`; staff `?preview=1` bypasses offline 503 gate. `homepage_builder.{html,css,js}`, EN/AR. +14 tests → 166 pass.
  - [x] (v0.5.0) Public catalog builder sidebar label translation: removed explicit lazy callback label and added `public_catalog_staff_builder` EN/AR discovery key; regression checks `Public Catalog Builder` / `منشئ المتجر العام`.
  - [x] (v0.5.0) Workspace dashboard sidebar label translation: added `workspace_dashboard` EN/AR key and DLux discovery regression for `common:workspace_dashboard` → `Workspace` / `مساحة العمل`.
  - [x] (v0.5.0) Shop-builder sidebar/write endpoint hardening: `mutation_endpoint` still mutates only on POST, passive GET/HEAD returns 204, browser-style GET navigation redirects to `/staff/shop-builder/`, discovery exposes only `public_catalog_staff:builder`; active public_catalog migrations stay single-file because app is unreleased. Tests cover discovery/navigation.
  - [x] (v0.5.0) Public Catalog Builder at `/staff/shop-builder/`: curate the public shop from live stock (publish/feature toggles, customize modal w/ image override, drag-reorder, live search/filters), AJAX endpoints gated by `change_publiccataloglisting`, transient-listing cards. Added `storefront_enabled`/`featured_limit` settings + `set_public_catalog_config`, coming-soon 503 gate on public views. `public_catalog/{staff_views,staff_urls}.py`, `shop_builder.{html,css,js}` `?v=20260712a`, EN/AR. +7 tests → 154 pass.
  - [x] (v0.5.0) Public contact modal + discovery cleanup: removed public Staff CTA, added fullscreen DLux dynamic-modal contact form at `/contact/modal/`, `PublicContactMessage` with unique idempotency key/email status/admin, one-email-per-key regression, and `sidebar_exclude=True` for landing/shop/contact/staff-entry callbacks.
  - [x] (v0.5.0) Public shop storefront makeover: image-led public hero, metrics/search/results header, richer product cards, detail/quick-view modal/contact sections, DLux-variable CSS `?v=20260712b`, and redaction/layout contract tests.
  - [x] (v0.4.2) DLux-owned public/staff split: internal URLs under `/staff/`, public `/` + `/shop/...`, `PublicCatalogListing` model/views/templates/modals, public-safe redaction tests, Caddy/Compose canonical host + legacy `erp` redirect, products/workspace app-pref saves use reversed `/staff/sys/api/preferences/app/...`, docs/changelog/VERSION updated.
  - [x] (v0.4.1) Release metadata correction: added CHANGELOG v0.4.1 for `django-lux[updater]>=1.4.4`; VERSION was 0.4.1 and the release is now tagged.
  - [x] (v0.4.0) Sales invoice POS catalog picker + cart (Idea 2): picker panel (Products/Services toggle + search + category) renders in-stock tiles client-side from new `_catalog_map` (variants-at-add as chips w/ stock; services get image or `SERVICE_TYPE_ICONS` icon). Picked → compact cart list (`_invoice_cart_row.html`) w/ editable price/qty, live subtotal, over-stock soft-warn, remove, + Custom line. `InvoiceItemForm` fields hidden except price/qty/desc; formset `extra=0`. Save path (`_apply_item_price`) untouched. New `sales/static/sales/{css,js}/invoice_editor.*` (reuses `.dlux-table-shell`). EN/AR. +4 tests, 2 updated. 134 pass.
  - [x] (v0.4.0) Per-user Products layout table/grid/light, resolved per-user override→global admin default→table (`catalog.product_layouts.get_products_layout`). Per-user pref in `Profile.preferences['app'][ns]`; GLOBAL default via dlux 1.4.4 `register_app_settings` → `SystemSettings.extra_config['app'][ns]['default_layout']`, read by `get_default_products_layout`/`get_app_system_config`. `ProductListView` branches: table=`ProductTable`, light=`ProductLightTable`, grid=`product_grid.html` store cards (variant swatches, expand→`scoped_modal_manager ?action=view`, `.dlux-table-shell`). Switch: header toggle + `/staff/sys/options` `register_card` picker (`catalog/dlux_options.py`); `products_layout.js` posts reversed staff app-pref URL. Added `{% block list_body %}` to `scoped_list.html`. EN/AR. Needs dlux≥1.4.4 (defensive import). +13 tests.
  - [x] (v0.4.0) Bumped host venv dlux 1.2.2→1.4.4 by symlinking site-packages/dlux → mounted source `../pkg-django-lux/dlux` (old moved to `.xpose/venv-site-packages/`); `requirements.txt` `>=1.4.4`; migrated dev sqlite up (catalog/dlux/finance/sales migrations). Full suite 130 pass; check clean.
  - [x] (v0.4.0) Stock-bearing color/size variants: added `ProductVariant`, `PurchaseInvoiceLine.variant`, `StockMovement.variant`, `InvoiceItem.variant` (`catalog/0006`, `sales/0007` with backfills). Opening Stock/Purchase rows create variant-linked IN movements without overwriting `Product.color/size`; sales issue/cancel guards per variant; product list/detail + sales editor show swatches/qty; invoice/purchase quantity errors get visible invalid cells.
  - [x] (v0.4.0) Rich demo seed + math stress tests: `seed_demo` now creates demo users/rates/suppliers/24 products/11 services/12 customers/4 purchase invoices/18 invoices/deposits/deliveries/expenses/staff ledger/stock takes; `--reset` clears new dependencies. Added financial decimal-chain, aggregate stock guard/cancel, stock-take variance, staff-ledger matrix tests. Full suite 112 pass + 1 skip.
  - [x] (v0.3.0) Workspace dashboard aether/rich-theme tile fix: `.workspace-tile`/drawer/empty/tools/chips now include `theme-aether` in the dark surface path, tile tone colors route through `--ws-*-rgb` vars with brighter dark-theme overrides for aether/prism/neon, template cache-bust `?v=20260710d`, and CSS regression test added. HTML/JS data contract unchanged.
  - [x] (v0.3.0) Themed report/form surfaces by REUSING dlux `.dlux-table-shell` (global; `--dlux-table-*` overridden by all 12 themes) — Dashboard/SalesReport/FinancialReport/InventoryValuation KPI tiles+panels use `.dlux-table-shell p-3` / list panels use it + `border-*`/`bg-transparent`; tables use native `.dlux-table-shell/.dlux-data-table`. Bespoke `report_surfaces.css`/`.rpt-card` (only 5 theme overrides, broke on others) retired → `.xpose/`. Invoice + purchase-invoice detail sections de-carded (`<section>`+`<h2>`). No view/Python changes. check + 96 tests + render probe (→.xpose) green.
  - [x] (v0.3.0) Scoped list browser tab titles: added `{% block title %}{{ page_title }}{% endblock %}` to `templates/common/scoped_list.html` so every `ScopedListView` page (stock takes/movements, purchase invoices) gets a real tab title (base.html renders `<app> | {block title}`, which was blank for generic lists). No per-model template change.
  - [x] (v0.3.0) Workspace dashboard restyled to match dlux Options cards (glass 1.4rem panels, `::before` tone accent bar via `--tile-accent-rgb`, icon badges, dashed grip, options chips, theme-dark overrides). CSS-only (`workspace_dashboard.css` `?v=20260710c`); JS/HTML data-contract untouched so reorder/hide/resize persist. Also fixed `.metric-value` number+currency: baseline inline-flex LTR pair + `text-align:start` so it stops colliding under Arabic RTL. check + 6 common tests green.
  - [x] (v0.3.0) Model plural label keys: added `models_<name>` alongside every `model_<name>` in finance/sales/catalog EN+AR (dlux resolve_model_label plural→singular→raw). Singular/plural parity verified all 3 apps both langs.
  - [x] (v0.3.0) Finance expenses + staff credit: `ExpenseCategory/Expense/StaffAccount/StaffLedgerEntry` (`finance/0003`), expense attachments via dlux archive widget, posted expenses feed financial report `operating_expenses/net_profit`, staff ledger signed balances + pending user confirmation through dlux notifications, confirm/dispute/void detail actions, workspace tiles/quick actions, role seed perms, AR/EN strings + tests.
  - [x] (v0.3.0) Product variants: nullable/blankable `Product.color/size`, `PurchaseInvoiceLine` snapshots (`catalog/0005`), and `InvoiceItem.color/size` sales snapshots (`sales/0006`); Product form excludes variants while list/detail show them; Opening Stock/Purchase intake use compact 15-color popover + Size/Spec; sales product lines select available variant metadata; purchase create starts with 1 row; AR/EN strings + focused tests.
  - [x] (v0.2.4) Workspace dashboard now at `/staff/workspace/`: project-wide dlux-themed tile grid with permission/scope/ownership-filtered finance/sales/delivery/catalog tiles, quick actions, hide/show drawer, per-user dlux app-preferences layout (`switch_pos.workspace_dashboard.v1`) with localStorage fallback, AR/EN strings + parity test; existing `/staff/sales/dashboard/` labeled Sales Overview.
  - [x] (v0.2.3) Purchase Invoice / inbound stock rework: added `Supplier`, `PurchaseInvoice`, `PurchaseInvoiceLine`, supplier combobox, product autofill grid, purchase attachment scan/PDF, list/detail/print with official logo + new-tab context print; posts Stock In movements linked by FK/reference; removed mistaken `Invoice.attachment` in merged `sales/0005`; Stock Movements now shows one-time Opening Stock/view-only record + Add Stock + Manual Movement.
  - [x] (v0.2.3) Opening Stock existing-product autofill now overwrites untouched row defaults (`0.00`, default unit) with selected product values for cost/markup/USD/LYD/category/unit/barcode, while preserving fields the user manually edited.
  - [x] (v0.2.3) Product/Opening Stock price sync: when `price_lyd_override` is filled, `cost_usd` changes now keep LYD fixed and recompute `price_usd` + `markup_percent`; blank LYD mode still keeps markup fixed and recomputes USD. `price_sync.js` supports `data-price-sync-row`; Opening Stock rows load it; extra modal scripts carry `?v=20260709a`.
  - [x] (v0.2.3) Individual payment receipts / إيصال قبض: `Payment.receipt_number` (`RCT-000001`, migration `sales/0005` backfill), print route `/staff/sales/payments/<id>/receipt/` gated by `sales.view_payment` + Payment ownership, links from invoice detail + payments list, receipt balance-after-payment math, invoice+receipt print headers use `APP_CONFIG.logo_url`, AR/EN strings, CHANGELOG/VERSION/docs updated.
  - [x] (v0.2.2) Fiscal-year financial report + exact COGS + invoice attachment; stock take + inventory valuation; catalog images; multi-column forms. Latest squashed migrations: `catalog/0003`, `sales/0004`.
  - [x] (v0.2.0) Per-employee row-level visibility for Invoice/Customer/Payment/Delivery/CashDeposit via `OWNER_FIELDS` + `view_all_*`; roles split into Manager/Rep/Courier.
  - [x] (v0.1.3-v0.1.5) Caddy edge + portfolio split, composer-updater topology, dashboard rates, customer/deposit comboboxes, translated filters/choices/permissions, seed demo.

### One-line info about last verified Tests:
2026-07-14: Public builder Options cleanup — `check`, `public_catalog` 32 pass, full suite 171 pass, `git diff --check`; homepage Options tile removed, catalog tile slimmed to identity/contact/default disclosure settings.

### One-line info about last time edited Docs:
CHANGELOG.md + docs/ARCHITECTURE.md — documented Homepage Builder Visual Studio config surface and v0.6.1 feature entry.

## Part 2: Global

### Global Standard Helpers, Shortcuts, Info, etc.:
- venv python: /Users/debeski/Desktop/depy/project-switch-pos/.venv/bin/python
- dev settings: config.settings_dev_sqlite
- dlux modal view: DynamicModalManagerView (show_table/show_form attrs); URL name `modal_manager`.
- dlux filter helpers: setup_filter_helper / advanced_filter_helper (utils/crud.py).

### Global Rulesets:
- Update CHANGELOG.md + docs same turn as feature/config changes. Tag-driven releases.

### Agent Handoff Rules:
- Confirm outward-facing / multi-file changes before sweeping edits.

### References and Links:
- CBL rates: https://cbl.gov.ly/currency-exchange-rates/ (static table; USD avg ~6.41).
