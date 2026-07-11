from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from catalog.models import Product, StockMovement, StockTake, StockTakeLine
from finance.models import ExchangeRate, Expense
from sales.models import Invoice, InvoiceItem, Payment
from sales.reports import build_financial_report, fiscal_year_window
from sales.services import cancel_invoice, issue_invoice


Q = Decimal("0.01")


class BusinessMathStressTests(TestCase):
    def test_financial_report_decimal_chain_with_discounts_expenses_receivables_and_inventory(self):
        ExchangeRate.objects.create(rate=Decimal("9.2500"))
        lock = Product.objects.create(name="Precision Lock", cost_usd=Decimal("12.35"), track_stock=True)
        sensor = Product.objects.create(name="Precision Sensor", cost_usd=Decimal("7.80"), track_stock=True)
        Product.objects.filter(pk=lock.pk).update(stock_qty=Decimal("19.55"))
        Product.objects.filter(pk=sensor.pk).update(stock_qty=Decimal("7.25"))

        inv = Invoice.objects.create(
            exchange_rate=Decimal("6.3333"),
            invoice_date=date(2026, 1, 15),
            discount_percent=Decimal("7.50"),
            status=Invoice.STATUS_ISSUED,
            customer_name="Decimal Buyer",
        )
        InvoiceItem.objects.create(
            invoice=inv,
            kind=InvoiceItem.KIND_PRODUCT,
            product=lock,
            description="Precision Lock",
            unit_price_lyd=Decimal("111.11"),
            quantity=Decimal("3.25"),
        )
        InvoiceItem.objects.create(
            invoice=inv,
            kind=InvoiceItem.KIND_PRODUCT,
            product=sensor,
            description="Precision Sensor",
            unit_price_lyd=Decimal("55.55"),
            quantity=Decimal("2.50"),
        )
        InvoiceItem.objects.create(
            invoice=inv,
            kind=InvoiceItem.KIND_SERVICE,
            description="Calibration",
            unit_price_lyd=Decimal("33.33"),
            quantity=Decimal("1.75"),
        )
        inv.recalc_totals()
        Payment.objects.create(invoice=inv, amount=Decimal("201.11"))
        inv.refresh_from_db()

        paid = Invoice.objects.create(
            exchange_rate=Decimal("8.1234"),
            invoice_date=date(2026, 2, 20),
            status=Invoice.STATUS_ISSUED,
            customer_name="Paid Buyer",
        )
        InvoiceItem.objects.create(
            invoice=paid,
            kind=InvoiceItem.KIND_PRODUCT,
            product=lock,
            description="Precision Lock",
            unit_price_lyd=Decimal("150.10"),
            quantity=Decimal("1.20"),
        )
        paid.recalc_totals()
        Payment.objects.create(invoice=paid, amount=paid.total_lyd)
        paid.refresh_from_db()

        Invoice.objects.create(
            exchange_rate=Decimal("6.0000"),
            invoice_date=date(2025, 12, 31),
            status=Invoice.STATUS_ISSUED,
            customer_name="Old Open Buyer",
            total_lyd=Decimal("77.77"),
            amount_paid=Decimal("0.00"),
        )
        Expense.objects.create(
            amount_lyd=Decimal("123.45"),
            expense_date=date(2026, 1, 31),
            status=Expense.STATUS_POSTED,
        )
        Expense.objects.create(
            amount_lyd=Decimal("999.99"),
            expense_date=date(2026, 1, 31),
            status=Expense.STATUS_DRAFT,
        )

        report = build_financial_report(*fiscal_year_window(2026))
        monthly = {row["month"].month: row["total"] for row in report["monthly"]}

        self.assertEqual(inv.subtotal_lyd, Decimal("558.32"))
        self.assertEqual(inv.discount_amount, Decimal("41.87"))
        self.assertEqual(inv.total_lyd, Decimal("516.45"))
        self.assertEqual(inv.status, Invoice.STATUS_PARTIAL)
        self.assertEqual(paid.total_lyd, Decimal("180.12"))
        self.assertEqual(paid.status, Invoice.STATUS_PAID)

        self.assertEqual(report["revenue"], Decimal("696.57"))
        self.assertEqual(report["cash_collected"], Decimal("381.23"))
        self.assertEqual(report["operating_expenses"], Decimal("123.45"))
        self.assertEqual(report["receivables"], Decimal("393.11"))
        self.assertEqual(report["inventory_value"], Decimal("2756.43"))
        self.assertEqual(report["cogs"].quantize(Q), Decimal("498.09"))
        self.assertEqual(report["gross_profit"].quantize(Q), Decimal("198.48"))
        self.assertEqual(report["net_profit"].quantize(Q), Decimal("75.03"))
        self.assertEqual(report["margin_percent"].quantize(Q), Decimal("28.49"))
        self.assertEqual(monthly[1], Decimal("516.45"))
        self.assertEqual(monthly[2], Decimal("180.12"))

    def test_issue_duplicate_product_lines_uses_aggregate_stock_guard_and_cancel_restores_exact_qty(self):
        ExchangeRate.objects.create(rate=Decimal("6.50"))
        product = Product.objects.create(name="Aggregate Lock", cost_usd=Decimal("10.00"), track_stock=True)
        StockMovement.objects.create(
            product=product,
            movement_type=StockMovement.TYPE_IN,
            quantity=Decimal("4.00"),
            reason="opening",
        )

        inv = Invoice.objects.create(exchange_rate=Decimal("6.50"), customer_name="Aggregate Buyer")
        InvoiceItem.objects.create(
            invoice=inv,
            kind=InvoiceItem.KIND_PRODUCT,
            product=product,
            description="Aggregate Lock A",
            unit_price_lyd=Decimal("65.00"),
            quantity=Decimal("2.50"),
        )
        second = InvoiceItem.objects.create(
            invoice=inv,
            kind=InvoiceItem.KIND_PRODUCT,
            product=product,
            description="Aggregate Lock B",
            unit_price_lyd=Decimal("65.00"),
            quantity=Decimal("1.60"),
        )
        inv.recalc_totals()

        with self.assertRaises(ValidationError):
            issue_invoice(inv, None)
        inv.refresh_from_db()
        product.refresh_from_db()
        self.assertEqual(inv.status, Invoice.STATUS_DRAFT)
        self.assertEqual(product.stock_qty, Decimal("4.00"))
        self.assertEqual(StockMovement.objects.filter(product=product, movement_type=StockMovement.TYPE_OUT).count(), 0)

        second.quantity = Decimal("1.50")
        second.save()
        inv.recalc_totals()
        issue_invoice(inv, None)
        inv.refresh_from_db()
        product.refresh_from_db()
        self.assertEqual(inv.status, Invoice.STATUS_ISSUED)
        self.assertEqual(inv.total_lyd, Decimal("260.00"))
        self.assertEqual(product.stock_qty, Decimal("0.00"))

        cancel_invoice(inv, None)
        inv.refresh_from_db()
        product.refresh_from_db()
        self.assertEqual(inv.status, Invoice.STATUS_CANCELLED)
        self.assertEqual(product.stock_qty, Decimal("4.00"))

    def test_stock_take_variance_value_and_apply_posts_signed_adjustment(self):
        ExchangeRate.objects.create(rate=Decimal("7.7500"))
        product = Product.objects.create(name="Counted Lock", cost_usd=Decimal("12.34"), track_stock=True)
        StockMovement.objects.create(
            product=product,
            movement_type=StockMovement.TYPE_IN,
            quantity=Decimal("10.00"),
            reason="opening",
        )
        product.refresh_from_db()
        take = StockTake.objects.create(count_date=date(2026, 3, 1))
        line = StockTakeLine.objects.create(
            stock_take=take,
            product=product,
            system_qty=product.stock_qty,
            counted_qty=Decimal("7.25"),
        )

        self.assertEqual(line.variance, Decimal("-2.75"))
        self.assertEqual(line.variance_value_lyd(), Decimal("-263.00"))
        self.assertEqual(take.total_variance_value_lyd, Decimal("-263.00"))

        take.apply()
        take.refresh_from_db()
        product.refresh_from_db()
        adjustment = StockMovement.objects.get(product=product, movement_type=StockMovement.TYPE_ADJUST)
        self.assertEqual(take.status, StockTake.STATUS_APPLIED)
        self.assertEqual(adjustment.quantity, Decimal("-2.75"))
        self.assertEqual(adjustment.signed_quantity, Decimal("-2.75"))
        self.assertEqual(product.stock_qty, Decimal("7.25"))
