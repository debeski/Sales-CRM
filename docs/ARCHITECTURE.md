# Switch POS — Architecture

A web-based sales system (منظومة مبيعات) for **Switch**, built on **DjangoLux (dlux 1.2.1)**.
It is an internal, single-branch system (not a public online store). DjangoLux already
provides users, permissions, sidebar/titlebar/navbar UI, dynamic modals, audit trail,
soft-delete, reports, backups and notifications — this project adds only the sales domain.

## Apps & dependency layering

```
finance   (money foundation: exchange rate + cash deposits)
   ▲
catalog   (products, services, stock ledger) — uses finance for conversion
   ▲
sales     (customers, invoices, items, payments) — uses catalog + finance
```

Lower layers **never** import higher ones. The stock ledger references invoices by
their string number (not a FK) so `catalog` stays independent of `sales`.

`common/` is a plain Python package (not a Django app, no models). It holds
`ScopedListView` and the generic `templates/common/scoped_list.html` so every
simple list page stays a few lines.

## How a screen is built (the dlux pattern)

For **simple models** (products, services, categories, rates, deposits, customers):

- One `ScopedListView` subclass per model (sets `model`, `table_class`,
  `filterset_class`, `permission_required`).
- Create / edit / view / delete are handled by the DjangoLux **dynamic modal
  manager** (`modal_manager`), which auto-resolves `<Model>Form` from the app's
  `forms.py`. No per-model create/update/delete views or templates needed.
- The list page's "Add" button and the `DluxTable` row context menu open those modals.

For the **invoice** (a multi-line document) we use custom full-page views
(`InvoiceCreateView` / `InvoiceUpdateView`) with a Django inline formset, plus
detail/issue/cancel/print/payment endpoints.

Naming convention is load-bearing: `<Model>Form`, `<Model>Table`, `<Model>Filter`
let dlux discovery wire modals, tables and filters automatically.

## Money & currency

`finance/services.py` is the **single source of conversion math**:

- `get_current_rate()` — the live USD→LYD rate (newest `ExchangeRate` row, cached).
- `usd_to_lyd()` / `lyd_to_usd()` / `quantize_lyd()` — consistent 2-dp rounding.

Reuse these everywhere instead of multiplying by a rate inline.

See [BUSINESS_RULES.md](BUSINESS_RULES.md) for pricing and the frozen-rate rule, and
[PERMISSIONS.md](PERMISSIONS.md) for the role model.

## Security baseline

- Every domain model extends `dlux.models.ScopedModel`: created/updated/deleted
  audit fields, soft-delete (`delete()` never hard-deletes), and optional scope
  isolation.
- Every view is `LoginRequiredMixin` + `PermissionRequiredMixin` with
  `raise_exception=True`; lifecycle actions (issue/cancel/confirm) are POST-only
  and permission-gated.
- Project security settings (CSP, CSRF/session cookies, HSTS) come from the dlux
  project scaffold in `config/settings.py`.
