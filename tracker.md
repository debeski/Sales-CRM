# Project Tracker (switch-pos) [Max 100 lines total]

## Part 1: Project Related

### Current Verified Snapshot:
Django POS/ERP on django-lux 1.3.2. Apps: finance, catalog, sales, common. USD-base pricing -> LYD via global ExchangeRate; sales invoices freeze rate/line prices/costs; purchase invoices post inbound stock. Caddy edge: erp.switchlibya.ly -> ERP; apex+www -> static portfolio. v0.2.3 in progress (untagged): receipts, print logo, dlux row menus/new-tab print, Opening Stock one-time intake, Purchase Invoices/Suppliers, row-scoped manual-LYD price sync. v0.2.2 tagged. Current test baseline: 91 pass.

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
  - [x] (v0.2.3) Purchase Invoice / inbound stock rework: added `Supplier`, `PurchaseInvoice`, `PurchaseInvoiceLine`, supplier combobox, product autofill grid, purchase attachment scan/PDF, list/detail/print with official logo + new-tab context print; posts Stock In movements linked by FK/reference; removed mistaken `Invoice.attachment` in merged `sales/0005`; Stock Movements now shows one-time Opening Stock/view-only record + Add Stock + Manual Movement.
  - [x] (v0.2.3) Opening Stock existing-product autofill now overwrites untouched row defaults (`0.00`, default unit) with selected product values for cost/markup/USD/LYD/category/unit/barcode, while preserving fields the user manually edited.
  - [x] (v0.2.3) Product/Opening Stock price sync: when `price_lyd_override` is filled, `cost_usd` changes now keep LYD fixed and recompute `price_usd` + `markup_percent`; blank LYD mode still keeps markup fixed and recomputes USD. `price_sync.js` supports `data-price-sync-row`; Opening Stock rows load it; extra modal scripts carry `?v=20260709a`.
  - [x] (v0.2.3) Opening Stock one-time bulk intake — a CHILD OF THE STOCK LEDGER, NOT its own model (user-directed pivot): trigger button on Stock Movements list (`stock_movement_list.html`) opens full-page grid `OpeningStockEditorView` (`/catalog/stock-movements/opening-stock/`). Plain `OpeningStockLineFormSet` (formset_factory) + per-row new-or-existing combobox (datalist + hidden id, autofill from product_map JSON). Submit (confirm) create-or-reuses Product, corrects price on edit, posts Stock In (reason "Opening balance", ref "OPENING"); zero-qty reprices w/o movement; blank rows dropped. No new perm (reuses add_product+add_stockmovement). Old model+migration `catalog/0004` + list/detail templates moved to `.xpose/`. +4 tests.
  - [x] (v0.2.3) Invoice/payment row actions now use standard dlux context menus: invoice rows expose view/print/edit/issue/cancel, payment rows expose view invoice/print receipt, and invoice-detail sub-payment rows expose print receipt; number/receipt cells are display-only; print actions use DjangoLux `target: "_blank"` URL actions (dlux core updated in `/Users/debeski/Desktop/depy/pkg-django-lux/dlux`).
  - [x] (v0.2.3) Individual payment receipts / إيصال قبض: `Payment.receipt_number` (`RCT-000001`, migration `sales/0005` backfill), print route `/sales/payments/<id>/receipt/` gated by `sales.view_payment` + Payment ownership, links from invoice detail + payments list, receipt balance-after-payment math, invoice+receipt print headers use `APP_CONFIG.logo_url`, AR/EN strings, CHANGELOG/VERSION/docs updated.
  - [x] (v0.2.2) Fiscal-year financial report + exact COGS + invoice attachment; stock take + inventory valuation; catalog images; multi-column forms. Latest squashed migrations: `catalog/0003`, `sales/0004`.
  - [x] (v0.2.0) Per-employee row-level visibility for Invoice/Customer/Payment/Delivery/CashDeposit via `OWNER_FIELDS` + `view_all_*`; roles split into Manager/Rep/Courier.
  - [x] (v0.1.3-v0.1.5) Caddy edge + portfolio split, composer-updater topology, dashboard rates, customer/deposit comboboxes, translated filters/choices/permissions, seed demo.

### One-line info about last verified Tests:
2026-07-10: 91 tests pass (`config.settings_dev_sqlite`) after merging sales `0006` into `0005`; `makemigrations --check --dry-run` and `git diff --check` clean.

### One-line info about last time edited Docs:
docs/BUSINESS_RULES.md, docs/OPERATIONS.md, docs/PERMISSIONS.md + CHANGELOG.md — documented Purchase Invoice/Supplier stock intake, attachment ownership, and Opening Stock one-time behavior.

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
