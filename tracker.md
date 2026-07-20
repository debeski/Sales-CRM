# Project Tracker (switch-pos) [Max 100 lines total]

## Part 1: Project Related [Max 55 lines]
### Current Verified Snapshot: [Max 5 lines]
- Django POS/ERP v0.6.4 after tagged v0.6.3; production pins `django-lux[updater]==1.4.9`; apps: finance, catalog, sales, common, public_catalog.
- Public `/`/`/shop/...`/`/contact/modal/`; staff under `/staff/...`; Caddy terminates automatic TLS for apex/www and redirects legacy ERP host.
- `VERSION`/`DLUX_APP_VERSION` and schema-1 `release-manifest.json` are version-locked; tagged images stamp `org.dlux.project.release-manifest` for Dlux update notes.
- Composer 1.1.11/Dlux 1.4.9 recovery uses terminal ack, self-exclusion, hardened socket access, and same-origin maintenance return; Caddy TLS/routing is unchanged.
- Current verified baseline: 175 tests pass; checks/migrations/Compose/workflow/manifest clean.
### Current Project Adopted Standards: [Max 5 lines]
- Scoped models via `dlux.ScopedModel`; lists use `common.ScopedListView` + Dlux modal manager.
- Money is frozen per invoice (`exchange_rate`, `unit_price_lyd`); finance is dependency root.
- Product variants own stock buckets; aggregate product stock remains for legacy no-variant lines.
- Row visibility uses `OWNER_FIELDS` + `view_all_<model>` and `common.access.apply_ownership` at read boundaries only.
- Public catalog is a curated projection; public contact writes are DB-idempotent.
### Adopted Standards' rules and policies: [Max 5 lines]
- Never delete files; move obsolete paths under `.xpose/` preserving relative paths.
- CSP and four-network isolation remain enforced; web has no egress or Docker API access.
- External rate fetches run in Celery; network changes require `./start.sh -d` recreation.
- Future reservation/purchase/checkout writes require DB-backed idempotency keys.
- Release changes update CHANGELOG/docs and keep tag, `VERSION`, and project manifest aligned.
### Cross-Cutting Audits if any: [Max 3 lines]
- 2026-07-18: Release/update path audit covers Caddy TLS, Composer recovery, baked Dlux gate, and project manifest metadata.
### Current Project's Unsolved Known Bugs: [Max 5 lines]
- Live VM likely runs stale Caddy/Compose: apex/www serve old portfolio while current repo proxies Django and redirects ERP.
- Deployment SMTP credentials are unset, so contact relay cannot authenticate.
- Local reused SQLite has obsolete `sales_invoice.attachment`; fresh migrated databases are correct.
### Incomplete Tasks: [Max 20 lines]
- **Priority 1:**
  - [ ] Publish Composer 1.1.11 and Dlux 1.4.9, publish Switch v0.6.4, recreate `composer-updater`, then submit a fresh update token.
  - [ ] Confirm the published v0.6.4 image exposes both baked-version and project-manifest labels in Dlux image review.
  - [ ] Reconcile the live VM Caddy/Compose deployment with current apex/www/ERP routing.
  - [ ] Publish initial listings and configure contact SMTP credentials.
  - [ ] Browser smoke-test modal edit/delete and the complete image-update recovery flow.
- **Priority 2:**
  - [ ] Design reservation/purchase/checkout models with idempotency constraints before adding public POST endpoints.
  - [ ] Optional: move per-list Add actions into filter bars instead of separate top-right buttons.
- **Completed Recently:**
  - [x] v0.6.4 adopted schema-1 project image release metadata with fail-closed CI validation and both-image label stamping.
  - [x] v0.6.4 added terminal image-update recovery, exact Dlux 1.4.9 gate, Composer hardening, and Caddy maintenance return.
  - [x] v0.6.2 isolated homepage preview language from the user session.
  - [x] v0.6.1 delivered Homepage Builder visual controls and public presentation variants.
  - [x] v0.5.1 delivered the live-preview Homepage Builder and removed workspace reset rehydration.
### One-line info about last verified Tests: [Max 5 lines]
- 2026-07-18: 175/175 tests, Django check, no missing migrations, manifest success/bad-tag failure, workflow YAML, base+dev Compose, py_compile, and diff checks pass.
- 2026-07-18: Production Compose still renders apex/www automatic TLS, ERP redirect host, and `https://switchlibya.ly`; Caddy files unchanged.
### One-line info about last time edited Docs: [Max 2 lines]
- 2026-07-18: README, RELEASING, OPERATIONS, and CHANGELOG document project manifest governance and Dlux image-review metadata.

## Part 2: Global [Max 20 lines]
### Global Standard Helpers, Shortcuts, Info, etc.:
- Venv: `../.venv/bin/python`; dev settings: `config.settings_dev_sqlite`.
- Validate releases with `python tools/validate_project_release_manifest.py --tag vX.Y.Z --repository debeski/Sales-CRM`.
### Global Rulesets:
- Keep tracker under 100 lines; preserve user work; update changelog/docs with feature/config changes.
### Agent Handoff Rules:
- Release rollout remains pending; do not report image labels live until the tagged image is built and inspected.
### References and Links:
- Dlux source: `../../pkg-django-lux`; release guide: `docs/RELEASING.md`; operations: `docs/OPERATIONS.md`.
