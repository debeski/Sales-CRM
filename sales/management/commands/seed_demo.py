"""
Seed realistic demo data for local testing / screenshots / demos.

Creates exchange rates, catalog (categories, products with barcodes + stock,
services), customers, and a spread of invoices across every status
(draft / issued / partial / paid / cancelled) with payments and cash deposits.

    python manage.py seed_demo            # idempotent top-up
    python manage.py seed_demo --reset    # wipe demo tables first (DESTRUCTIVE)

Reference data (rates / catalog / customers) is idempotent via get_or_create.
Sample invoices + deposits are only created when none exist yet (or after
--reset) so re-running never piles up duplicate invoices.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from catalog.models import Category, Product, Service, StockMovement
from finance.models import CashDeposit, ExchangeRate
from sales.models import Customer, Invoice, InvoiceItem, Payment
from sales.services import cancel_invoice, issue_invoice

D = lambda v: Decimal(str(v))  # noqa: E731 — terse Decimal helper for readability


class Command(BaseCommand):
    help = "Seed demo data (rates, catalog, customers, invoices, payments) for testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing demo data before seeding (DESTRUCTIVE).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.actor = get_user_model().objects.filter(is_superuser=True).first()

        if options["reset"]:
            self._reset()

        self._seed_rates()
        cats = self._seed_categories()
        products = self._seed_products(cats)
        services = self._seed_services()
        customers = self._seed_customers()

        if Invoice.objects.exists():
            self.stdout.write(self.style.WARNING(
                "Invoices already exist — skipping sample invoices. Re-run with --reset to rebuild."
            ))
        else:
            self._seed_invoices(products, services, customers)
            self._seed_deposits()

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self._summary()

    # ---------------------------------------------------------------- reset ---
    def _reset(self):
        # Order matters: clear the stock ledger before products (PROTECT), and
        # invoices (which SET_NULL/CASCADE their children) before customers/rates.
        Payment.objects.all().delete()
        InvoiceItem.objects.all().delete()
        Invoice.objects.all().delete()
        StockMovement.objects.all().delete()
        Product.objects.all().delete()
        Service.objects.all().delete()
        Category.objects.all().delete()
        Customer.objects.all().delete()
        CashDeposit.objects.all().delete()
        ExchangeRate.objects.all().delete()
        self.stdout.write(self.style.WARNING("Reset: demo tables cleared."))

    # ------------------------------------------------------------- reference ---
    def _seed_rates(self):
        # Append-only history; the newest row is the live rate. Create the
        # official rate first, then the (higher) black-market one so it wins.
        ExchangeRate.objects.get_or_create(
            rate=D("6.41"), source=ExchangeRate.SOURCE_OFFICIAL,
            defaults={"note": "Seed: CBL official"},
        )
        rate, _ = ExchangeRate.objects.get_or_create(
            rate=D("8.50"), source=ExchangeRate.SOURCE_BLACK_MARKET,
            defaults={"note": "Seed: parallel-market"},
        )
        return rate

    def _seed_categories(self):
        names = ["Smart Locks", "Spare Parts", "Accessories"]
        return {
            n: Category.objects.get_or_create(name=n, defaults={"is_active": True})[0]
            for n in names
        }

    def _seed_products(self, cats):
        # (name, category, barcode, cost_usd, markup%, unit, reorder, initial_stock,
        #  lyd_override, track_stock)
        specs = [
            ("Switch Pro Deadbolt", "Smart Locks", "6291041500213", 85, 30, "piece", 5, 40, None, True),
            ("Switch Lite Keypad", "Smart Locks", "6291041500220", 45, 35, "piece", 5, 3, None, True),   # low stock
            ("Fingerprint Module", "Spare Parts", "6291041500237", 18, 40, "piece", 10, 60, None, True),
            ("Spare Key Fob", "Accessories", "6291041500244", 4, 50, "piece", 20, 12, None, True),        # low stock
            ("Mounting Plate", "Spare Parts", "6291041500251", 6, 25, "piece", 15, 80, None, True),
            ("Gift Card (unrelated goods)", "Accessories", "6291041500268", 0, 0, "piece", 0, 0, D("250.00"), False),
        ]
        out = {}
        for name, cat, barcode, cost, markup, unit, reorder, stock, override, track in specs:
            p, created = Product.objects.get_or_create(
                name=name,
                defaults={
                    "category": cats[cat],
                    "barcode": barcode,
                    "cost_usd": D(cost),
                    "markup_percent": D(markup),
                    "unit": unit,
                    "reorder_level": D(reorder),
                    "price_lyd_override": override,
                    "track_stock": track,
                },
            )
            # Seed opening stock exactly once (idempotent: only if no ledger rows).
            if created and track and stock and not p.movements.exists():
                StockMovement.objects.create(
                    product=p, movement_type=StockMovement.TYPE_IN,
                    quantity=D(stock), reason="Seed: opening stock",
                )
            out[name] = p
        return out

    def _seed_services(self):
        specs = [
            ("Standard Installation", Service.TYPE_INSTALLATION, 20),
            ("Annual Maintenance", Service.TYPE_MAINTENANCE, 35),
            ("Extended Warranty", Service.TYPE_WARRANTY, 15),
            ("City Delivery", Service.TYPE_DELIVERY, 10),
            ("Custom Job (quote)", Service.TYPE_OTHER, None),
        ]
        return {
            name: Service.objects.get_or_create(
                name=name,
                defaults={"service_type": stype, "price_usd": (D(price) if price is not None else None)},
            )[0]
            for name, stype, price in specs
        }

    def _seed_customers(self):
        specs = [
            ("Ahmed Al-Mansouri", "0913001122", "Tripoli, Gargaresh Rd"),
            ("Sara Trading Co.", "0925004433", "Benghazi, Dubai St"),
            ("Khalid Enterprises", "0918887766", "Misrata, Tripoli St"),
            ("Fatima Interiors", "0947001199", "Zawiya, Central Market"),
        ]
        return [
            Customer.objects.get_or_create(
                name=name, defaults={"phone": phone, "address": addr},
            )[0]
            for name, phone, addr in specs
        ]

    # ------------------------------------------------------------- invoices ---
    def _add_line(self, inv, spec):
        kind = spec[0]
        if kind == "product":
            p, qty = spec[1], D(spec[2])
            InvoiceItem.objects.create(
                invoice=inv, kind=InvoiceItem.KIND_PRODUCT, product=p, description=p.name,
                unit_price_lyd=p.selling_price_lyd(inv.exchange_rate) or D(0),
                unit_price_usd=p.effective_price_usd, quantity=qty,
            )
        elif kind == "service":
            s, qty = spec[1], D(spec[2])
            InvoiceItem.objects.create(
                invoice=inv, kind=InvoiceItem.KIND_SERVICE, service=s, description=s.name,
                unit_price_lyd=s.selling_price_lyd(inv.exchange_rate) or D(0),
                unit_price_usd=s.price_usd, quantity=qty,
            )
        else:  # ("custom", description, unit_price_lyd, qty)
            InvoiceItem.objects.create(
                invoice=inv, kind=InvoiceItem.KIND_CUSTOM, description=spec[1],
                unit_price_lyd=D(spec[2]), quantity=D(spec[3]),
            )

    def _invoice(self, *, customer=None, name="", lines, status="draft",
                 discount_percent=0, days_ago=0, pay_fraction=None):
        inv = Invoice(
            customer=customer,
            customer_name=name or (customer.name if customer else ""),
            discount_percent=D(discount_percent),
            invoice_date=timezone.localdate() - timedelta(days=days_ago),
        )
        if customer:
            inv.customer_phone = customer.phone
            inv.customer_address = customer.address
        inv.save()  # assigns number + freezes the current exchange rate

        for spec in lines:
            self._add_line(inv, spec)
        inv.recalc_totals()

        if status in ("issued", "partial", "paid", "cancelled"):
            issue_invoice(inv, self.actor)
            inv.refresh_from_db()
            if status in ("partial", "paid"):
                frac = D(1) if status == "paid" else (pay_fraction or D("0.5"))
                amount = (inv.total_lyd * frac).quantize(D("0.01"))
                if amount > 0:
                    Payment.objects.create(invoice=inv, amount=amount, method=Payment.METHOD_CASH)
            if status == "cancelled":
                cancel_invoice(inv, self.actor)
        return inv

    def _seed_invoices(self, products, services, customers):
        P, S = products, services
        self._invoice(
            customer=customers[0], status="paid", days_ago=6,
            lines=[("product", P["Switch Pro Deadbolt"], 1), ("service", S["Standard Installation"], 1)],
        )
        self._invoice(
            customer=customers[1], status="partial", days_ago=4, pay_fraction=D("0.4"),
            lines=[("product", P["Switch Lite Keypad"], 2), ("product", P["Spare Key Fob"], 3)],
        )
        self._invoice(
            customer=customers[2], status="issued", days_ago=2, discount_percent=10,
            lines=[("product", P["Fingerprint Module"], 2), ("service", S["Annual Maintenance"], 1)],
        )
        self._invoice(
            customer=customers[3], status="cancelled", days_ago=8,
            lines=[("product", P["Mounting Plate"], 4)],
        )
        self._invoice(
            name="Walk-in — Omar", status="draft", days_ago=0,
            lines=[("custom", "On-site consultation", 150, 1), ("service", S["City Delivery"], 1)],
        )
        self._invoice(
            customer=customers[0], status="paid", days_ago=1,
            lines=[("product", P["Gift Card (unrelated goods)"], 2)],
        )

    def _seed_deposits(self):
        CashDeposit.objects.get_or_create(
            reference="DEP-0001",
            defaults={"amount": D("500.00"), "method": CashDeposit.METHOD_CASH},
        )
        dep, created = CashDeposit.objects.get_or_create(
            reference="DEP-0002",
            defaults={"amount": D("1250.00"), "method": CashDeposit.METHOD_BANK},
        )
        if created:
            dep.confirm(self.actor)

    # -------------------------------------------------------------- summary ---
    def _summary(self):
        rows = [
            ("Exchange rates", ExchangeRate.objects.count()),
            ("Categories", Category.objects.count()),
            ("Products", Product.objects.count()),
            ("Services", Service.objects.count()),
            ("Customers", Customer.objects.count()),
            ("Invoices", Invoice.objects.count()),
            ("Payments", Payment.objects.count()),
            ("Cash deposits", CashDeposit.objects.count()),
        ]
        for label, count in rows:
            self.stdout.write(f"  {label:<16} {count}")
