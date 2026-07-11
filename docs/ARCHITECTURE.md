# Switch POS — Architecture

A web-based sales system (منظومة مبيعات) for **Switch**, built on **DjangoLux (dlux 1.4.4)**.
It is an internal, single-branch system (not a public online store). DjangoLux already
provides users, permissions, sidebar/titlebar/navbar UI, dynamic modals, audit trail,
soft-delete, reports, backups and notifications — this project adds only the sales domain.

## Apps & dependency layering

```
finance   (money foundation: exchange rate, cash deposits, expenses, staff accounts)
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
detail/issue/cancel/print/payment endpoints. The line editor is a POS-style
**catalog picker + cart**: `_catalog_map` serialises in-stock products (with
their in-stock `ProductVariant`s) and services (image or `service_type` icon);
`invoice_editor.js` renders a filterable tile grid where a colour/size variant is
picked *at add-time* and dropped into a cart list (`_invoice_cart_row.html`) with
editable price/qty. The formset fields (`product/service/variant/color/size/kind`)
are hidden inputs the picker fills; the server save path (`_apply_item_price` +
the per-variant issue/cancel stock guard) is unchanged.

Naming convention is load-bearing: `<Model>Form`, `<Model>Table`, `<Model>Filter`
let dlux discovery wire modals, tables and filters automatically.

## Per-user Products layout (table / grid / light)

The Products page renders three ways. The effective layout resolves
**per-user override → global admin default → `table`**, in
`catalog/product_layouts.py::get_products_layout(request)`:

- **Per-user override** — `Profile.preferences['app']['switch_pos.products_layout']`
  (a scalar; same app-preference store as the workspace dashboard).
- **Global admin default** — a superuser setting saved to
  `SystemSettings.extra_config['app']['switch_pos.products_layout']['default_layout']`,
  registered with dlux 1.4.4's `register_app_settings` (a settings tile in the
  Options admin grid) and read via `dlux.utils.get_app_system_config`.

`ProductListView` branches on the resolved value:

- **table** — the full `ProductTable`.
- **light** — a minimal `ProductLightTable` (name · price · stock · active); the
  rest stays in the record's dlux detail modal (`Product.get_modal_context`).
- **grid** — `catalog/product_grid.html`, a store-style card grid (image, price,
  stock, in-stock colour/size variants) whose Expand action opens the same dlux
  detail modal the table rows use (`scoped_modal_manager … ?action=view`). Reuses
  the table's filtered + paginated rows and the themed `.dlux-table-shell` surface.

Per-user switching has two surfaces sharing one component
(`catalog/_products_layout_toggle.html`) and one script
(`catalog/js/products_layout.js`, persists via the global
`window.updateAppPreference` then reloads): an inline header toggle and a
`/sys/options` card registered with `dlux.options.register_card`
(`catalog/dlux_options.py`, gated on `catalog.view_product`). The global default
is the superuser settings tile above (`register_app_settings`). The shared
`templates/common/scoped_list.html` exposes a `{% block list_body %}` so alternate
layouts can replace the table body while keeping the header, filter and modal-CRUD
wiring. **Requires dlux ≥ 1.4.4** (`register_app_settings` + `get_app_system_config`);
registrations import defensively so an older runtime still gets the per-user card.

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
