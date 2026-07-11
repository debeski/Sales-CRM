# Project Tracker (switch-pos) [Max 100 lines total]

## Part 1: Project Related

### Current Verified Snapshot:
Django POS/ERP on django-lux 1.4.4 (host venv now symlinked to mounted source `../pkg-django-lux/dlux`, same as dev compose). Apps: finance, catalog, sales, common. USD-base pricing -> LYD via ExchangeRate; sales invoices freeze rate/line prices/costs; purchase/opening stock post inbound stock. v0.3.0 is tagged; VERSION/CHANGELOG at v0.4.0 (seed/math tests, stock-bearing variants, per-user+global Products layout). Current baseline: 130 pass, 0 skip.

### Current Project Adopted Standards:
- Scoped models via dlux ScopedModel; list pages via common.ScopedListView + dlux modal_manager.
- Money frozen per-invoice (exchange_rate + unit_price_lyd). finance is dependency root.
- Stock variants are `ProductVariant(product,color,size,stock_qty)` buckets; `StockMovement.variant` updates product aggregate + variant qty; legacy no-variant lines use aggregate product stock.
- Filters use dlux setup_filter_helper; forms use dlux set_field_attrs.
- Row-level visibility (v0.2.0): owned models set `OWNER_FIELDS` + `view_all_<model>` perm; `common.access.apply_ownership` at READ choke points only (NOT the manager — keeps child recalcs whole). Roles: superuser / Sales Manager / Sales Representative / Delivery Courier via `seed_roles`.

### Adopted Standards' rules and policies:
- Never delete: move to ./.xpose/ preserving path.
- CSP active + network isolation (v0.1.4 3+1 model): `internal` is `internal:true`; egress bridge = smtp-relay/dlux-updater/celery/composer-updater; `frontend`=Caddy ingress; `docker_proxy` (internal) = composer-updater↔docker-socket-proxy. web is cache-only for scraped data.
- External data (rate scrapes) runs in celery; web reads Redis cache. Network changes need `./start.sh -d` (recreate), not `-r`.

### Cross-Cutting Audits if any:
Audit done 2026-07-02: barcode already present; migrations clean; no scraping deps yet.

### Current Project's Unsolved Known Bugs:
- Local dev sqlite drift only: leftover NOT NULL `sales_invoice.attachment` column (sqlite never dropped it post-v0.2.3) breaks `seed_demo` on that file. Schema from migrations is correct (tests green on fresh DB); recreate dev DB to clear.

### Incomplete Tasks:
- **Priority 1:**
  - [ ] Optional: inject per-list Add button into the filter bar (config "buttons") vs current separate top-right button.
  - [ ] Browser smoke-test modal edit/delete (row actions) — combobox verified via test client.
- **Completed Recently:**
  - [x] (v0.4.0) Sales invoice POS catalog picker + cart (Idea 2): picker panel (Products/Services toggle + search + category) renders in-stock tiles client-side from new `_catalog_map` (variants-at-add as chips w/ stock; services get image or `SERVICE_TYPE_ICONS` icon). Picked → compact cart list (`_invoice_cart_row.html`) w/ editable price/qty, live subtotal, over-stock soft-warn, remove, + Custom line. `InvoiceItemForm` fields hidden except price/qty/desc; formset `extra=0`. Save path (`_apply_item_price`) untouched. New `sales/static/sales/{css,js}/invoice_editor.*` (reuses `.dlux-table-shell`). EN/AR. +4 tests, 2 updated. 134 pass.
  - [x] (v0.4.0) Per-user Products layout table/grid/light, resolved per-user override→global admin default→table (`catalog.product_layouts.get_products_layout`). Per-user pref in `Profile.preferences['app'][ns]`; GLOBAL default via dlux 1.4.4 `register_app_settings` → `SystemSettings.extra_config['app'][ns]['default_layout']`, read by `get_default_products_layout`/`get_app_system_config`. `ProductListView` branches: table=`ProductTable`, light=`ProductLightTable`, grid=`product_grid.html` store cards (variant swatches, expand→`scoped_modal_manager ?action=view`, `.dlux-table-shell`). Switch: header toggle + `/sys/options` `register_card` picker (`catalog/dlux_options.py`); `products_layout.js`→`window.updateAppPreference`. Added `{% block list_body %}` to `scoped_list.html`. EN/AR. Needs dlux≥1.4.4 (defensive import). +13 tests.
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
  - [x] (v0.2.4) Workspace dashboard `/workspace/`: project-wide dlux-themed tile grid with permission/scope/ownership-filtered finance/sales/delivery/catalog tiles, quick actions, hide/show drawer, per-user dlux app-preferences layout (`switch_pos.workspace_dashboard.v1`) with localStorage fallback, AR/EN strings + parity test; existing `/sales/dashboard/` renamed visibly to Sales Overview.
  - [x] (v0.2.3) Purchase Invoice / inbound stock rework: added `Supplier`, `PurchaseInvoice`, `PurchaseInvoiceLine`, supplier combobox, product autofill grid, purchase attachment scan/PDF, list/detail/print with official logo + new-tab context print; posts Stock In movements linked by FK/reference; removed mistaken `Invoice.attachment` in merged `sales/0005`; Stock Movements now shows one-time Opening Stock/view-only record + Add Stock + Manual Movement.
  - [x] (v0.2.3) Opening Stock existing-product autofill now overwrites untouched row defaults (`0.00`, default unit) with selected product values for cost/markup/USD/LYD/category/unit/barcode, while preserving fields the user manually edited.
  - [x] (v0.2.3) Product/Opening Stock price sync: when `price_lyd_override` is filled, `cost_usd` changes now keep LYD fixed and recompute `price_usd` + `markup_percent`; blank LYD mode still keeps markup fixed and recomputes USD. `price_sync.js` supports `data-price-sync-row`; Opening Stock rows load it; extra modal scripts carry `?v=20260709a`.
  - [x] (v0.2.3) Individual payment receipts / إيصال قبض: `Payment.receipt_number` (`RCT-000001`, migration `sales/0005` backfill), print route `/sales/payments/<id>/receipt/` gated by `sales.view_payment` + Payment ownership, links from invoice detail + payments list, receipt balance-after-payment math, invoice+receipt print headers use `APP_CONFIG.logo_url`, AR/EN strings, CHANGELOG/VERSION/docs updated.
  - [x] (v0.2.2) Fiscal-year financial report + exact COGS + invoice attachment; stock take + inventory valuation; catalog images; multi-column forms. Latest squashed migrations: `catalog/0003`, `sales/0004`.
  - [x] (v0.2.0) Per-employee row-level visibility for Invoice/Customer/Payment/Delivery/CashDeposit via `OWNER_FIELDS` + `view_all_*`; roles split into Manager/Rep/Courier.
  - [x] (v0.1.3-v0.1.5) Caddy edge + portfolio split, composer-updater topology, dashboard rates, customer/deposit comboboxes, translated filters/choices/permissions, seed demo.

### One-line info about last verified Tests:
2026-07-11: dlux 1.4.4 — full suite 134 pass, 0 skip; project `makemigrations --check` clean (no new migrations for invoice-picker makeover — form/formset only).

### One-line info about last time edited Docs:
docs/ARCHITECTURE.md — Products layout section now documents per-user→global-default→table resolution + `register_app_settings`; header dlux version → 1.4.4.

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
