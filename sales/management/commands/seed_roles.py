"""
Create the project's permission groups so the owner doesn't have to tick boxes.

  * "Sales Staff" — technicians & delivery reps. They can pull products, create
    and issue invoices, take payments, and record their cash deposits. They
    CANNOT touch prices, the exchange rate, the catalog, or confirm deposits.
  * Admins are expected to be Django superusers (full access). The owner runs
    everything; this command just wires the limited staff role.

Run:  python manage.py seed_roles
Idempotent — safe to re-run after adding models/permissions.
"""
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

STAFF_PERMS = [
    # Sell
    "sales.view_invoice",
    "sales.add_invoice",
    "sales.change_invoice",      # edit own drafts before issuing
    "sales.issue_invoice",
    "sales.view_payment",
    "sales.add_payment",
    "sales.view_customer",
    "sales.add_customer",
    # Look up what to sell (read-only)
    "catalog.view_product",
    "catalog.view_service",
    # Hand over cash (record only; an admin confirms)
    "finance.view_cashdeposit",
    "finance.add_cashdeposit",
]

GROUPS = {"Sales Staff": STAFF_PERMS}


class Command(BaseCommand):
    help = "Create/refresh the Switch POS permission groups."

    def handle(self, *args, **options):
        for group_name, perm_codes in GROUPS.items():
            group, _ = Group.objects.get_or_create(name=group_name)
            perms = []
            for code in perm_codes:
                app_label, codename = code.split(".", 1)
                try:
                    perms.append(
                        Permission.objects.get(
                            content_type__app_label=app_label, codename=codename
                        )
                    )
                except Permission.DoesNotExist:
                    self.stderr.write(self.style.WARNING(f"  missing permission: {code}"))
            group.permissions.set(perms)
            self.stdout.write(self.style.SUCCESS(f"{group_name}: {len(perms)} permissions set"))
        self.stdout.write("Done. Assign staff users to the 'Sales Staff' group; keep the owner as a superuser.")
