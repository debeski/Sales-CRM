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
