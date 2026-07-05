# Switch POS — Roles & Permissions

DjangoLux provides the user/group/permission system (model-level). On top of it
this project adds **row-level visibility**: the same view permission shows a rep
only their own records but a manager the whole store. See
[`common/access.py`](../common/access.py) and [ARCHITECTURE.md](ARCHITECTURE.md).

## Two layers

1. **Model-level (Django/dlux)** — *can this user touch invoices at all?* Enforced
   by `PermissionRequiredMixin` on every view (`raise_exception=True` → 403). Also
   drives the auto-discovered sidebar: no `view_delivery` → no "Deliveries" entry.
2. **Row-level (this project)** — *which invoices?* Each owned model declares an
   `OWNER_FIELDS` tuple and gains a `view_all_<model>` permission. A user sees a
   row if they are a **superuser**, hold **`view_all_<model>`**, or **own** it
   (they match one of `OWNER_FIELDS`). A model without `OWNER_FIELDS` (product
   catalog, exchange rates) is shared — never row-filtered.

| Model | Owned by (`OWNER_FIELDS`) | "See everyone's" permission |
|-------|---------------------------|-----------------------------|
| `Invoice` | `salesperson`, `created_by` | `sales.view_all_invoice` |
| `Customer` | `created_by` | `sales.view_all_customer` |
| `Payment` | `created_by`, `invoice.salesperson` | `sales.view_all_payment` |
| `Delivery` | `assigned_to`, `created_by` | `sales.view_all_delivery` |
| `finance.CashDeposit` | `created_by` | `finance.view_all_cashdeposit` |

## Roles

| Role | Who | Group | Visibility |
|------|-----|-------|------------|
| **Admin / Owner** | المسؤول | Django **superuser** | Everything |
| **Sales Manager** | مدير المبيعات | **"Sales Manager"** | All reps' invoices/customers/payments/deliveries (holds every `view_all_*`), assigns salespeople & couriers, runs reports, manages catalog + rate, confirms deposits |
| **Sales Representative** | مندوب المبيعات | **"Sales Representative"** | **Own** invoices/customers/payments only (no `view_all_*`) |
| **Delivery Courier** | مندوب التوصيل | **"Delivery Courier"** | **Only deliveries assigned to them**; records cash collected. No access to invoices, reports, or the sales figures on the dashboard |

An invoice's `salesperson` defaults to whoever creates it; only a Manager
(`assign_salesperson`) can reassign it. Same for a delivery's `assigned_to`
(`assign_delivery`).

## Seed the groups

```bash
python manage.py seed_roles
```

Idempotent — safe to re-run after adding models/permissions. Creates/refreshes
**Sales Manager**, **Sales Representative**, and **Delivery Courier** with the
permission sets in [`sales/management/commands/seed_roles.py`](../sales/management/commands/seed_roles.py).

## Custom permissions defined by the project

| Permission | Model | Meaning |
|------------|-------|---------|
| `sales.issue_invoice` | Invoice | Finalize a draft (draws down stock) |
| `sales.cancel_invoice` | Invoice | Cancel an invoice (restores stock) |
| `sales.view_sales_report` | Invoice | View sales reports + XLSX export |
| `sales.view_all_invoice` | Invoice | See every rep's invoices, not just own |
| `sales.assign_salesperson` | Invoice | Reassign an invoice's salesperson |
| `sales.view_all_customer` | Customer | See every rep's customers |
| `sales.view_all_payment` | Payment | See every rep's payments |
| `sales.view_all_delivery` | Delivery | See all deliveries, not just assigned |
| `sales.assign_delivery` | Delivery | Assign deliveries to couriers |
| `finance.confirm_cashdeposit` | CashDeposit | Confirm / reject deposits |
| `finance.view_all_cashdeposit` | CashDeposit | See every staffer's deposits |

Standard `view/add/change/delete` permissions exist for every model. Reports and
the dashboard's sales figures are additionally row-scoped by the viewer.

## Assigning a user

1. Create the user (DjangoLux user management UI or admin).
2. Add them to **exactly one** of the three groups.
3. Keep the owner as a superuser.

Because reps/couriers lack the `view_all_*` permissions, they automatically see
only their own rows — no per-user configuration needed.
