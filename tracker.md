# Project Tracker (switch-pos) [Max 100 lines total]

## Part 1: Project Related

### Current Verified Snapshot:
Django POS on django-lux 1.2.14. Apps: finance, catalog, sales, common. USD-base pricing → LYD via global ExchangeRate. Postgres/Redis/Celery(+beat via `-B`) via compose. v0.1.2 in progress (untagged). Migrations clean; 15 tests pass.

### Current Project Adopted Standards:
- Scoped models via dlux ScopedModel; list pages via common.ScopedListView + dlux modal_manager.
- Money frozen per-invoice (exchange_rate + unit_price_lyd). finance is dependency root.
- Filters use dlux setup_filter_helper; forms use dlux set_field_attrs.

### Adopted Standards' rules and policies:
- Never delete: move to ./.xpose/ preserving path.
- CSP active + network isolation: `switch_pos_internal` is `internal:true`. Egress only via smtp-relay and now celery (`switch_pos_net`). web is cache-only for scraped data.
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
17 tests pass (config.settings_dev_sqlite); incl. finance CBL + EAN scraper tests; system check clean.

### One-line info about last time edited Docs:
docs/OPERATIONS.md — added Celery Beat/CBL-rate section + combobox note (v0.1.2).

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
