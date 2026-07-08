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
editing cost recomputes the USD price (markup held), and the live LYD price is shown
as the manual-LYD field's **placeholder**. Typing a value into that field turns it into
a real fixed override (and back-fills USD + markup to match). The detail view adds a
computed **"Selling Price (LYD)"** row (via `get_modal_context`) so it matches the list.

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

## Catalog images

Products and Services carry an optional photo (`image`). It's shown as a thumbnail
in the catalog lists and enlarged in the item's detail card. On a phone the upload
field offers the camera or the gallery. Purely descriptive — it never affects
pricing, stock or invoices.

## Inventory

- `Product.stock_qty` is **only** changed through `StockMovement` (the ledger is
  authoritative); it is not editable on the product form. Seed initial quantity
  with a "Stock In" movement.
- Movements are applied atomically (`F()` expression) on insert.
- Low stock = `track_stock and stock_qty ≤ reorder_level` (shown on the dashboard).

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

## Invoice attachment

An invoice may carry an optional **attachment** — a scan or photo of the signed
paper invoice (or a supporting document, image or PDF). It's captured with the
rich file field (drag-drop, phone camera, or a desktop scanner) and shown as a
link on the invoice's page. Purely a record; it never affects totals.

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
