from decimal import Decimal

from django.test import SimpleTestCase, TestCase

from catalog.models import Category, Product, Service
from finance.models import ExchangeRate
from sales.models import Invoice, InvoiceItem, Payment
from sales.services import cancel_invoice, issue_invoice

from ..urls import app_name


class SalesConfigScaffoldTests(SimpleTestCase):
    def test_urls_namespace_matches_app_name(self):
        self.assertEqual(app_name, "sales")


class PricingAndInvoiceTests(TestCase):
    def setUp(self):
        ExchangeRate.objects.create(rate=Decimal("6.50"))
        self.cat = Category.objects.create(name="Locks")
        self.product = Product.objects.create(
            name="Lock X1", category=self.cat,
            cost_usd=Decimal("40"), markup_percent=Decimal("25"),
        )
        self.service = Service.objects.create(
            name="Install", service_type="installation", price_usd=Decimal("20"),
        )

    def test_hybrid_pricing(self):
        # 40 USD + 25% = 50 USD -> * 6.50 = 325 LYD
        self.assertEqual(self.product.effective_price_usd, Decimal("50.00"))
        self.assertEqual(self.product.selling_price_lyd(), Decimal("325.00"))
        # Manual LYD override wins over conversion
        self.product.price_lyd_override = Decimal("400.00")
        self.assertEqual(self.product.selling_price_lyd(), Decimal("400.00"))

    def test_service_per_job_when_unpriced(self):
        svc = Service.objects.create(name="Custom job", service_type="other")
        self.assertIsNone(svc.selling_price_lyd())

    def test_auto_sku_and_invoice_number(self):
        self.assertTrue(self.product.sku.startswith("P"))
        inv = Invoice.objects.create(customer_name="Walk-in")
        self.assertTrue(inv.number.startswith("INV-"))
        self.assertEqual(inv.exchange_rate, Decimal("6.5000"))

    def test_issue_deducts_stock_and_freezes_total(self):
        from catalog.models import StockMovement
        StockMovement.objects.create(product=self.product, movement_type="in", quantity=Decimal("10"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_qty, Decimal("10.00"))

        inv = Invoice.objects.create(customer_name="Walk-in")
        InvoiceItem.objects.create(
            invoice=inv, product=self.product, description="Lock X1",
            unit_price_lyd=Decimal("325"), quantity=Decimal("2"),
        )
        inv.recalc_totals()
        self.assertEqual(inv.total_lyd, Decimal("650.00"))

        issue_invoice(inv, None)
        inv.refresh_from_db(); self.product.refresh_from_db()
        self.assertEqual(inv.status, Invoice.STATUS_ISSUED)
        self.assertEqual(self.product.stock_qty, Decimal("8.00"))

        # A later rate change must NOT alter this issued invoice's total.
        ExchangeRate.objects.create(rate=Decimal("9.99"))
        inv.refresh_from_db()
        self.assertEqual(inv.total_lyd, Decimal("650.00"))
        self.assertEqual(inv.exchange_rate, Decimal("6.5000"))

    def test_payment_status_transitions(self):
        inv = Invoice.objects.create(customer_name="Walk-in")
        InvoiceItem.objects.create(
            invoice=inv, service=self.service, kind="service", description="Install",
            unit_price_lyd=Decimal("130"), quantity=Decimal("1"),
        )
        inv.recalc_totals()
        issue_invoice(inv, None)

        Payment.objects.create(invoice=inv, amount=Decimal("50"))
        inv.refresh_from_db()
        self.assertEqual(inv.status, Invoice.STATUS_PARTIAL)
        self.assertEqual(inv.balance_due, Decimal("80.00"))

        Payment.objects.create(invoice=inv, amount=Decimal("80"))
        inv.refresh_from_db()
        self.assertEqual(inv.status, Invoice.STATUS_PAID)
        self.assertEqual(inv.balance_due, Decimal("0.00"))

    def test_issue_blocks_on_insufficient_stock(self):
        from django.core.exceptions import ValidationError
        from catalog.models import StockMovement
        StockMovement.objects.create(product=self.product, movement_type="in", quantity=Decimal("1"))
        inv = Invoice.objects.create(customer_name="Walk-in")
        InvoiceItem.objects.create(
            invoice=inv, product=self.product, description="Lock X1",
            unit_price_lyd=Decimal("325"), quantity=Decimal("3"),
        )
        inv.recalc_totals()
        with self.assertRaises(ValidationError):
            issue_invoice(inv, None)
        inv.refresh_from_db(); self.product.refresh_from_db()
        # Nothing changed: still a draft, stock untouched.
        self.assertEqual(inv.status, Invoice.STATUS_DRAFT)
        self.assertEqual(self.product.stock_qty, Decimal("1.00"))

    def test_sales_report_aggregates(self):
        from sales.reports import build_sales_report, build_sales_report_xlsx, default_window
        from catalog.models import StockMovement
        StockMovement.objects.create(product=self.product, movement_type="in", quantity=Decimal("10"))
        inv = Invoice.objects.create(customer_name="Acme")
        InvoiceItem.objects.create(
            invoice=inv, product=self.product, description="Lock X1",
            unit_price_lyd=Decimal("325"), quantity=Decimal("2"),
        )
        inv.recalc_totals()
        issue_invoice(inv, None)
        Payment.objects.create(invoice=inv, amount=Decimal("300"))

        df, dt = default_window()
        report = build_sales_report(df, dt)
        self.assertEqual(report["invoice_count"], 1)
        self.assertEqual(report["total_sales"], Decimal("650.00"))
        self.assertEqual(report["outstanding"], Decimal("350.00"))
        self.assertEqual(report["by_product"][0]["description"], "Lock X1")
        # XLSX builds and is a non-empty zip (xlsx magic bytes "PK").
        content = build_sales_report_xlsx(report)
        self.assertTrue(content.startswith(b"PK"))

    def test_cancel_restores_stock(self):
        from catalog.models import StockMovement
        StockMovement.objects.create(product=self.product, movement_type="in", quantity=Decimal("5"))
        inv = Invoice.objects.create(customer_name="Walk-in")
        InvoiceItem.objects.create(
            invoice=inv, product=self.product, description="Lock X1",
            unit_price_lyd=Decimal("325"), quantity=Decimal("3"),
        )
        inv.recalc_totals()
        issue_invoice(inv, None)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_qty, Decimal("2.00"))

        cancel_invoice(inv, None)
        inv.refresh_from_db(); self.product.refresh_from_db()
        self.assertEqual(inv.status, Invoice.STATUS_CANCELLED)
        self.assertEqual(self.product.stock_qty, Decimal("5.00"))


class CustomerComboboxSyncTests(TestCase):
    """_InvoiceEditorView._sync_customer binds/creates the Customer for the typed
    name and persists contact info so it autofills on re-entry."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        # A superuser bypasses row-ownership, so these tests exercise the
        # bind/create logic itself (not the private-customer filtering).
        self.actor = get_user_model().objects.create_superuser("comboadmin", "a@a.co", "x")

    def _sync(self, **kwargs):
        from sales.views import InvoiceCreateView
        inv = Invoice(exchange_rate=Decimal("6.50"), **kwargs)
        InvoiceCreateView()._sync_customer(inv, self.actor)
        return inv

    def test_new_name_creates_and_persists_customer(self):
        from sales.models import Customer
        inv = self._sync(customer_name="New Buyer", customer_phone="0910", customer_address="Old City")
        self.assertIsNotNone(inv.customer_id)
        cust = Customer.objects.get(name="New Buyer")
        self.assertEqual((cust.phone, cust.address), ("0910", "Old City"))

    def test_existing_name_reused_and_backfills_snapshot(self):
        from sales.models import Customer
        existing = Customer.objects.create(name="Acme", phone="0999")
        inv = self._sync(customer_name="acme", customer_phone="", customer_address="")
        self.assertEqual(inv.customer_id, existing.pk)  # matched case-insensitively
        self.assertEqual(inv.customer_phone, "0999")  # snapshot backfilled from record
        self.assertEqual(Customer.objects.filter(name__iexact="acme").count(), 1)  # no duplicate

    def test_unnamed_walk_in_creates_no_customer(self):
        from sales.models import Customer
        inv = self._sync(customer_name="")
        self.assertIsNone(inv.customer_id)
        self.assertEqual(Customer.objects.count(), 0)


class PaymentFormTests(TestCase):
    def test_quick_pay_validates_without_paid_at(self):
        # The inline quick-pay form submits only amount/method/deposit; paid_at
        # must not be required (it defaults to now on save).
        from sales.forms import PaymentForm

        form = PaymentForm({"amount": "50", "method": "cash", "deposit": ""})
        self.assertTrue(form.is_valid(), form.errors)

        inv = Invoice.objects.create(customer_name="X", status=Invoice.STATUS_ISSUED)
        payment = form.save(commit=False)
        payment.invoice = inv
        payment.save()
        self.assertIsNotNone(payment.paid_at)  # model default applied
        inv.refresh_from_db()
        self.assertEqual(inv.amount_paid, Decimal("50.00"))


class DepositBatchTests(TestCase):
    def setUp(self):
        ExchangeRate.objects.create(rate=Decimal("6.50"))
        self.inv = Invoice.objects.create(
            customer_name="X", status=Invoice.STATUS_ISSUED, total_lyd=Decimal("1000")
        )

    def test_deposit_amount_autosums_linked_payments(self):
        from finance.models import CashDeposit

        dep = CashDeposit.objects.create(reference="B", amount=Decimal("0.00"))
        Payment.objects.create(invoice=self.inv, amount=Decimal("320"), deposit=dep)
        dep.refresh_from_db()
        self.assertEqual(dep.amount, Decimal("320.00"))

        Payment.objects.create(invoice=self.inv, amount=Decimal("100"), deposit=dep)
        dep.refresh_from_db()
        self.assertEqual(dep.amount, Decimal("420.00"))  # grows

        dep.payments.order_by("-pk").first().delete()
        dep.refresh_from_db()
        self.assertEqual(dep.amount, Decimal("320.00"))  # shrinks

    def test_reassigning_a_payment_recomputes_both_batches(self):
        from finance.models import CashDeposit

        a = CashDeposit.objects.create(reference="A", amount=Decimal("0.00"))
        b = CashDeposit.objects.create(reference="B", amount=Decimal("0.00"))
        p = Payment.objects.create(invoice=self.inv, amount=Decimal("200"), deposit=a)
        a.refresh_from_db(); self.assertEqual(a.amount, Decimal("200.00"))

        p.deposit = b
        p.save()
        a.refresh_from_db(); b.refresh_from_db()
        self.assertEqual(a.amount, Decimal("0.00"))    # old batch emptied
        self.assertEqual(b.amount, Decimal("200.00"))  # new batch carries it

    def test_sync_deposit_creates_then_reuses_by_reference(self):
        from django.test import RequestFactory
        from django.contrib.auth import get_user_model
        from finance.models import CashDeposit
        from sales.views import PaymentCreateView

        req = RequestFactory().post("/")
        req.user = get_user_model().objects.create(username="u1")
        view = PaymentCreateView()

        p1 = Payment(invoice=self.inv, amount=Decimal("50"), method="cash")
        view._sync_deposit(req, p1, "Shift-1")
        self.assertIsNotNone(p1.deposit_id)
        self.assertEqual(p1.deposit.reference, "Shift-1")

        p2 = Payment(invoice=self.inv, amount=Decimal("10"), method="cash")
        view._sync_deposit(req, p2, "shift-1")  # case-insensitive match
        self.assertEqual(p2.deposit_id, p1.deposit_id)
        self.assertEqual(CashDeposit.objects.filter(reference__iexact="shift-1").count(), 1)

        p3 = Payment(invoice=self.inv, amount=Decimal("10"), method="cash")
        view._sync_deposit(req, p3, "")  # blank -> no batch
        self.assertIsNone(p3.deposit_id)


class SeedDemoCommandTests(TestCase):
    def test_seed_demo_spread_idempotent_and_reset(self):
        from django.core.management import call_command
        from catalog.models import Product

        call_command("seed_demo", verbosity=0)
        self.assertTrue(Product.objects.filter(barcode="6291041500213").exists())
        for status in ("paid", "partial", "issued", "cancelled", "draft"):
            self.assertTrue(
                Invoice.objects.filter(status=status).exists(),
                f"expected a {status} invoice",
            )
        self.assertTrue(Payment.objects.exists())

        # Re-running does not pile up duplicate invoices.
        count = Invoice.objects.count()
        call_command("seed_demo", verbosity=0)
        self.assertEqual(Invoice.objects.count(), count)

        # --reset wipes then rebuilds to the same shape.
        call_command("seed_demo", "--reset", verbosity=0)
        self.assertEqual(Invoice.objects.count(), count)
