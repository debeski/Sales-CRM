"""
Fiscal-year financial report — revenue, COGS estimate, gross profit, cash,
receivables, inventory value.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import RequestFactory, TestCase

from catalog.models import Product
from finance.models import ExchangeRate, Expense
from sales.models import Invoice, InvoiceItem, Payment
from sales.reports import available_fiscal_years, build_financial_report, fiscal_year_window
from sales.views import FinancialReportView

User = get_user_model()
rf = RequestFactory()


class FiscalWindowTests(TestCase):
    def test_window_is_calendar_year(self):
        self.assertEqual(fiscal_year_window(2026), (date(2026, 1, 1), date(2026, 12, 31)))

    def test_available_years_span_first_invoice_to_now(self):
        this_year = date.today().year
        self.assertEqual(available_fiscal_years()[0], this_year)  # newest first, always includes now


class FinancialReportTests(TestCase):
    def setUp(self):
        ExchangeRate.objects.create(rate=Decimal("5.00"))
        self.p = Product.objects.create(name="P", cost_usd=Decimal("2.00"), track_stock=True)
        Product.objects.filter(pk=self.p.pk).update(stock_qty=Decimal("10"))
        inv = Invoice.objects.create(exchange_rate=Decimal("5.00"), status=Invoice.STATUS_ISSUED, customer_name="X")
        InvoiceItem.objects.create(
            invoice=inv, kind=InvoiceItem.KIND_PRODUCT, product=self.p,
            description="P", unit_price_lyd=Decimal("50.00"), quantity=Decimal("3"),
        )
        inv.recalc_totals()          # total_lyd = 3 × 50 = 150
        Payment.objects.create(invoice=inv, amount=Decimal("100.00"))  # → partial
        self.inv = inv

    def test_report_figures(self):
        year = self.inv.invoice_date.year
        d1, d2 = fiscal_year_window(year)
        r = build_financial_report(d1, d2)
        self.assertEqual(r["revenue"], Decimal("150.00"))
        self.assertEqual(r["invoice_count"], 1)
        self.assertEqual(r["cogs"], Decimal("30.00"))          # 3 × 2 USD × rate 5
        self.assertEqual(r["gross_profit"], Decimal("120.00"))
        self.assertEqual(r["operating_expenses"], Decimal("0.00"))
        self.assertEqual(r["net_profit"], Decimal("120.00"))
        self.assertEqual(r["margin_percent"].quantize(Decimal("0.1")), Decimal("80.0"))
        self.assertEqual(r["cash_collected"], Decimal("100.00"))
        self.assertEqual(r["receivables"], Decimal("50.00"))   # 150 − 100 outstanding
        self.assertEqual(r["inventory_value"], Decimal("100.00"))  # 10 × 2 USD × 5
        self.assertEqual(len(r["monthly"]), 1)

    def test_posted_expenses_reduce_net_profit(self):
        year = self.inv.invoice_date.year
        d1, d2 = fiscal_year_window(year)
        Expense.objects.create(
            amount_lyd=Decimal("35.00"),
            expense_date=self.inv.invoice_date,
            status=Expense.STATUS_POSTED,
            reference="rent",
        )
        Expense.objects.create(
            amount_lyd=Decimal("15.00"),
            expense_date=self.inv.invoice_date,
            status=Expense.STATUS_DRAFT,
            reference="not posted",
        )

        r = build_financial_report(d1, d2)

        self.assertEqual(r["gross_profit"], Decimal("120.00"))
        self.assertEqual(r["operating_expenses"], Decimal("35.00"))
        self.assertEqual(r["net_profit"], Decimal("85.00"))

    def test_cogs_uses_frozen_line_cost(self):
        # Cost is frozen on the line at sale time — changing the product's cost
        # later must NOT change historical COGS.
        year = self.inv.invoice_date.year
        d1, d2 = fiscal_year_window(year)
        Product.objects.filter(pk=self.p.pk).update(cost_usd=Decimal("99.00"))
        r = build_financial_report(d1, d2)
        self.assertEqual(r["cogs"], Decimal("30.00"))  # still 3 × frozen 2 × 5, not 99
        line = self.inv.items.first()
        self.assertEqual(line.unit_cost_usd, Decimal("2.00"))  # frozen on save

    def test_report_is_whole_store_not_row_scoped(self):
        # build_financial_report takes no actor — a second rep's data is included.
        other = User.objects.create_user("rep2", password="x")
        inv2 = Invoice.objects.create(exchange_rate=Decimal("5.00"), status=Invoice.STATUS_ISSUED,
                                      customer_name="Y", created_by=other, salesperson=other)
        InvoiceItem.objects.create(invoice=inv2, kind=InvoiceItem.KIND_CUSTOM,
                                   description="misc", unit_price_lyd=Decimal("10.00"), quantity=Decimal("1"))
        inv2.recalc_totals()
        d1, d2 = fiscal_year_window(self.inv.invoice_date.year)
        r = build_financial_report(d1, d2)
        self.assertEqual(r["revenue"], Decimal("160.00"))  # 150 + 10, both reps
        self.assertEqual(r["invoice_count"], 2)

    def test_view_requires_perm_and_defaults_to_current_year(self):
        user = User.objects.create_user("mgr", password="x")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="sales", codename="view_financial_report")
        )
        user = User.objects.get(pk=user.pk)
        req = rf.get("/sales/financial/")
        req.user = user
        view = FinancialReportView()
        view.request, view.args, view.kwargs = req, (), {}
        ctx = view.get_context_data()
        self.assertEqual(ctx["year"], date.today().year)
        self.assertIn("report", ctx)
