# Switch POS — Roles & Permissions

DjangoLux provides the user/group/permission system. This project defines domain
permissions and one limited staff group.

## Roles

| Role | Who | How |
|------|-----|-----|
| **Admin / Owner** | المسؤول — runs everything | Django **superuser** (full access) |
| **Sales Staff** | الفنيين ومنذوبي التوصيل (technicians, delivery reps) | Member of the **"Sales Staff"** group |

The owner described staff as users who "just pull stock, issue an invoice, and
manage a cash deposit" — nothing more.

## Seed the staff group

```bash
python manage.py seed_roles
```

Idempotent. Creates/refreshes **"Sales Staff"** with exactly:

- `sales`: view/add/change invoice, **issue_invoice**, view/add payment, view/add customer
- `catalog`: **view** product, **view** service (read-only — cannot change prices)
- `finance`: view/add cash deposit (record only)

Staff explicitly **cannot**: set the exchange rate, edit the catalog/prices, confirm
cash deposits, or cancel invoices.

## Custom permissions defined by the project

| Permission | Model | Meaning |
|------------|-------|---------|
| `finance.manage_exchangerate` | ExchangeRate | Set the global USD→LYD rate |
| `finance.confirm_cashdeposit` | CashDeposit | Confirm / reject deposits |
| `sales.issue_invoice` | Invoice | Finalize a draft (draws down stock) |
| `sales.cancel_invoice` | Invoice | Cancel an invoice (restores stock) |
| `sales.view_sales_report` | Invoice | View sales reports + XLSX export (owner-only; not granted to staff) |

Standard `view/add/change/delete` permissions exist for every model. All views are
gated with `PermissionRequiredMixin` (`raise_exception=True` → 403, not a redirect).

## Assigning a staff user

1. Create the user (DjangoLux user management UI or admin).
2. Add them to the **Sales Staff** group.
3. Keep the owner as a superuser.
