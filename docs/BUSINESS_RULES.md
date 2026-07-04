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

## Inventory

- `Product.stock_qty` is **only** changed through `StockMovement` (the ledger is
  authoritative); it is not editable on the product form. Seed initial quantity
  with a "Stock In" movement.
- Movements are applied atomically (`F()` expression) on insert.
- Low stock = `track_stock and stock_qty ≤ reorder_level` (shown on the dashboard).

## Cash deposits (ايداع نقدي)

Technicians and delivery reps **record** the cash they collected (`pending`); an
admin **confirms** or **rejects** it. Invoice payments may reference the deposit
that carried their cash so the books reconcile.
