# Switch POS — Business Rules

## Currency

- Switch imports from China and thinks in **USD**; it sells locally in **LYD**.
- LYD prices follow the **black-market** USD rate (higher than the official rate),
  which the admin sets globally.
- The rate is a global setting reused by every price and conversion. It lives in
  `finance.ExchangeRate` as an **append-only history**; the newest row is the live
  rate. Past rows are never edited, giving a full audit trail of rate movements.

## Pricing model — hybrid (USD base + optional LYD override)

Decided with the owner. For each `Product`:

1. Cost is stored in USD (`cost_usd`). A `markup_percent` (or an explicit
   `price_usd`) yields the **USD selling price** (`effective_price_usd`).
   `Product.save()` **persists** this derived `price_usd` when only cost + markup
   were entered, so the stored record (and its detail view) never shows 0.
2. The **LYD selling price** is derived live: `effective_price_usd × current_rate`.
   Change the rate once and every product's LYD price updates everywhere.
3. Any item may set a manual **`price_lyd_override`** — a fixed LYD price that
   bypasses conversion (for odd / unrelated goods Switch occasionally resells).
   Left blank, the item sells at the live rate (the default).

The create/edit form keeps these fields in step as you type (`catalog/js/price_sync.js`):
editing markup recomputes the USD price, editing the USD price recomputes the markup,
editing cost recomputes the USD price (markup held) while the manual LYD override is
blank, and the live LYD price is shown as the manual-LYD field's **placeholder**.
Typing a value into that field turns it into a real fixed override (and back-fills
USD + markup to match); while that override is present, changing the cost keeps the
LYD price fixed and recalculates the implied USD price + markup from the new cost.
The detail view adds a computed **"Selling Price (LYD)"** row (via
`get_modal_context`) so it matches the list.

`Service` items follow the same override logic and may also be **"per job"**
(no fixed price — entered on the invoice).

## Frozen rate per invoice

When an invoice is created it captures the current rate into `Invoice.exchange_rate`,
and every line stores its own frozen `unit_price_lyd`. **Later rate changes never
rewrite a past invoice's totals.** This is correct accounting and matches the owner's
expectation that an issued invoice is final.

## Invoice lifecycle

```
draft ──issue──▶ issued ──payment──▶ partial ──payment──▶ paid
  │                  │
  └───── (edit) ─────┘ (only drafts are editable)
issued/partial/paid ──cancel──▶ cancelled  (stock restored)
```

- **Draft**: editable; no stock impact.
- **Issue** (`issue_invoice`): snapshots the rate record and **draws down stock**
  (a `StockMovement` OUT per product line). Requires at least one item. **Blocked**
  if any tracked product would go negative — demand is summed per product across
  lines and the issue is refused (nothing changes) with the shortages named.
- **Payments**: each `Payment` updates `amount_paid` and advances status
  (`issued → partial → paid`). Payments link optionally to a `CashDeposit`.
- **Cancel** (`cancel_invoice`): if the invoice had drawn stock, it is **restored**
  via reversing `StockMovement` IN rows.
- In the invoice and payment lists, row actions live in the standard **DjangoLux
  context menu** (right-click, long-press, or double-click primary action). The
  invoice number / receipt number columns are display values, not hidden action
  triggers. Print actions from those menus open in a new browser tab so the
  current workflow is not replaced.

## Payment receipts (إيصال قبض)

Every recorded `Payment` has its own durable receipt number
(`Payment.receipt_number`, generated as `RCT-000001` style and backfilled for
existing payments by migration `sales/0005`). Staff can print the receipt from
the row context menu in the invoice's payments table or the standalone payments
list at `/sales/payments/<id>/receipt/`; receipt print actions open in a new tab.

The receipt uses the same official logo from DjangoLux System Settings as the
printed invoice. It shows the customer/invoice, amount collected, method,
payment time, receiving user, optional cash-deposit reference, amount paid before
this receipt, and the invoice balance **after this specific receipt**. It is
gated by `sales.view_payment` and the same `Payment` row ownership rules as the
payments list, so a rep cannot open another rep's receipt by guessing the URL.

## Catalog images

Products and Services carry an optional photo (`image`). It's shown as a thumbnail
in the catalog lists and enlarged in the item's detail card. On a phone the upload
field offers the camera or the gallery. Purely descriptive — it never affects
pricing, stock or invoices.

## Inventory

- `Product.stock_qty` is **only** changed through `StockMovement` (the ledger is
  authoritative); it is not editable on the product form. Use Opening Stock once
  for first adoption, Purchase Invoices for normal inbound stock, and manual
  Stock Movements only for one-off corrections/adjustments.
- Movements are applied atomically (`F()` expression) on insert.
- Low stock = `track_stock and stock_qty ≤ reorder_level` (shown on the dashboard).

## Opening stock (one-time bulk intake / رصيد افتتاحي)

For **first adoption**: load everything already on the shelf in one pass, rather
than adding each product and then reconstructing history invoice-by-invoice. An
**opening balance** is *what is physically in storage now* — already net of
anything sold before go-live — so there's nothing to reconcile. Past sales are
simply not re-entered; real invoices start drawing down stock from launch on.

This is **not a document of its own** — it's a *child of the stock ledger*: a
one-time bulk way to post Stock In movements. A **trigger button on the Stock
Movements page** (gated by `add_product` + `add_stockmovement`) opens a full-page
grid (`/catalog/stock-movements/opening-stock/`) where an admin enters many items
at once, one per row:

1. Each row is either a **new** item (type a name) or an **existing** one (pick
   it from the datalist — cost/markup/price/category/unit/barcode autofill).
   Fields: name, category, unit, barcode, import cost (USD), markup %, selling
   price (USD), optional manual LYD price, and **quantity in storage**. Purchase
   shop and date are intentionally omitted (irrelevant for an opening balance).
   Pricing cells use the same row-scoped live sync as the Product form: markup,
   USD selling price, cost, and manual LYD override stay consistent inside that
   row without changing any neighbouring row. Selecting an existing product
   overwrites untouched row defaults (`0.00`, default unit) with that product's
   current values, but preserves fields the user already edited by hand.
2. **Submitting** (behind a confirm describing what will happen) runs one
   transaction: each row create-or-reuses its `Product`, corrects its pricing
   when the admin edited those cells, and posts one **Stock In** `StockMovement`
   for the stored quantity (`reason="Opening balance"`, `reference="OPENING"`).
   Stock still flows only through the ledger. A zero-quantity row reprices its
   product without posting a movement; blank rows are dropped.
3. It can only be applied once. After `reference="OPENING"` movements exist, the
   Stock Movements page switches the action to a read-only Opening Stock record
   at `/catalog/stock-movements/opening-stock/view/`; the posted movements remain
   the authoritative audit trail.

## Purchase invoices / inbound stock invoices

For stock bought **after** launch, use **Catalog → Purchase Invoices** (or the
**Add Stock** button on Stock Movements). A purchase invoice is the robust
inbound-stock document that Opening Stock was never meant to be:

1. Header fields capture the supplier and invoice metadata. The supplier name is
   a search-and-add combobox like customer entry on sales invoices: choosing an
   existing supplier autofills phone/address, while a new name creates a
   `Supplier` record and snapshots supplier name/phone/address onto the invoice.
2. The line grid reuses the Opening Stock product behavior. Each row is a new or
   existing `Product`; selecting an existing item autofills category, unit,
   barcode, import cost, markup, USD selling price, and manual LYD price. Edits
   to cost/markup/USD/manual-LYD use the same row-scoped price-sync rules as the
   Product form.
3. Submitting the invoice runs one transaction: it saves a `PurchaseInvoice` +
   `PurchaseInvoiceLine` snapshots, creates or updates the products, and posts
   one Stock In `StockMovement` per line with `reference=<purchase invoice no.>`
   and `purchase_invoice` linked. This keeps `Product.stock_qty` ledger-driven
   while giving staff an invoice-like document to view/print later.
4. Purchase invoices may carry the scan/photo/PDF attachment of the supplier's
   paper invoice (`PurchaseInvoice.attachment`, upload path
   `purchase_invoices/`). This is record-only and never affects totals or stock.

## Stock take (physical inventory count / جرد)

The **annual (or periodic) inventory count**. You count what's physically on the
shelves and reconcile it against what the system thinks you have:

1. Start a count (`StockTake`) — it snapshots the current system quantity for
   every active stock-tracked product and gives you a sheet to enter the counted
   quantity per item (blank = not counted). Opens in `open` status.
2. The count's page shows a **variance report**: system vs counted, the signed
   variance, and the LYD value of each discrepancy (variance × unit cost).
3. **Apply** it (needs `apply_stocktake`) — the system posts one **Adjustment**
   `StockMovement` per real discrepancy on a tracked product, so `stock_qty`
   becomes the counted figure, and the take locks as `applied` (can't re-apply).
   Adjustments flow through the same append-only ledger as every other stock
   change, so the correction is fully auditable.

Apply promptly after counting: the adjustment is `counted − system-snapshot`, so
a sale between the snapshot and applying would skew it.

## Inventory valuation

A read-only report of **what the stock on hand is worth right now** —
Σ(`stock_qty` × `cost_usd`), shown in USD and converted to LYD at the live rate.
This is the closing-stock figure the fiscal-year financial report uses. Gated
by `view_inventory_valuation`.

## Fiscal year & the financial report

A **fiscal year** here is the calendar year (Jan 1 – Dec 31), which is the norm
in Libya. The **financial report** (`/sales/financial/`, gated by
`view_financial_report`) is a whole-store owner P&L for a chosen year — it is
never per-rep. It reports:

- **Period figures** (for the selected year): **revenue** (issued/partial/paid
  invoices), **cost of goods (estimate)**, **gross profit** + margin, and **cash
  collected** (payments received in the year).
- **Current snapshots** (point-in-time, labelled *current*): **outstanding
  receivables** and **inventory value**.

**COGS is exact**: each invoice line freezes the product's unit cost at the time
of sale (`InvoiceItem.unit_cost_usd`), just like it freezes the selling price and
rate — so a later cost change never rewrites a past invoice's profit. COGS =
Σ(quantity × frozen unit cost × the invoice's frozen rate). Lines created before
cost-freezing was added fall back to the product's current cost.

## Purchase invoice attachment

Customer-facing sales invoices do **not** carry scan/PDF attachments. The
supporting scan/photo/PDF belongs to the inbound **Purchase Invoice** because it
represents the supplier document used to add stock. It is captured with the rich
file field (drag-drop, phone camera, or desktop scanner) and shown as a link on
the purchase invoice page.

## Cash deposits (ايداع نقدي)

Technicians and delivery reps **record** the cash they collected (`pending`); an
admin **confirms** or **rejects** it. Invoice payments may reference the deposit
that carried their cash so the books reconcile. A staffer sees only the deposits
they recorded; a manager (`view_all_cashdeposit`) sees all.

## Who sees what (per-employee visibility)

The system is multi-user: each record is owned, and staff see only their own work
unless they hold the matching `view_all_<model>` permission. Full rules in
[PERMISSIONS.md](PERMISSIONS.md). In business terms:

- A **sales rep** sees only **their own** invoices, customers and payments. Their
  customer book is private (two reps can each keep a "Mr. Ali" without collision).
  Their dashboard sales figures and reports cover **only their own sales**.
- An invoice belongs to its **salesperson** (defaults to whoever created it). Only
  a **manager** can reassign it to another rep.
- A **manager** sees and reports on the **whole store**, and assigns work.
- The **owner** is a superuser and sees everything.

## Deliveries

A **delivery** is a courier job — optionally linked to an invoice, with a
recipient/address snapshot so it stays intact if the invoice changes. Lifecycle:
`pending → assigned → out → delivered` (or `failed` / `cancelled`). It
auto-advances to *assigned* the moment a courier is set, and stamps the delivery
time on *delivered*. A **courier sees only the jobs assigned to them** and never
the sales side of the business; a **dispatcher/manager** (`view_all_delivery` +
`assign_delivery`) sees the whole board and assigns couriers.
