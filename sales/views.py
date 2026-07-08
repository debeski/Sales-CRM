import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import DetailView, TemplateView

from dlux.utils import log_user_action

from common.access import apply_ownership, user_can_view_all
from common.views import ScopedListView, scope_filtered_queryset
from finance.models import CashDeposit, ExchangeRate
from finance.services import (
    get_cbl_official_rate,
    get_current_rate,
    get_ean_black_market_rate,
    has_configured_rate,
)

from .filters import CustomerFilter, DeliveryFilter, InvoiceFilter, PaymentFilter
from .forms import CustomerForm, InvoiceForm, InvoiceItemFormSet, PaymentForm
from .models import Customer, Delivery, Invoice, Payment
from .reports import (
    available_fiscal_years,
    build_financial_report,
    build_sales_report,
    build_sales_report_xlsx,
    fiscal_year_window,
    parse_window,
)
from .services import cancel_invoice, issue_invoice
from .tables import CustomerTable, DeliveryTable, InvoiceTable, PaymentTable


def _visible_invoices(user):
    """Invoices this user is allowed to see/act on (own + assigned, or all for a
    manager holding ``view_all_invoice``). The single ownership choke point for
    the full-page invoice flows that bypass ScopedListView."""
    return apply_ownership(Invoice.objects.all(), user)


# --------------------------------------------------------------------------- #
# Simple list pages
# --------------------------------------------------------------------------- #
class CustomerListView(ScopedListView):
    model = Customer
    permission_required = "sales.view_customer"
    table_class = CustomerTable
    filterset_class = CustomerFilter
    page_title_key = "page_customers"


class DeliveryListView(ScopedListView):
    model = Delivery
    permission_required = "sales.view_delivery"
    table_class = DeliveryTable
    filterset_class = DeliveryFilter
    page_title_key = "page_deliveries"


class PaymentListView(ScopedListView):
    model = Payment
    permission_required = "sales.view_payment"
    table_class = PaymentTable
    filterset_class = PaymentFilter
    page_title_key = "page_payments"
    allow_add = False


class InvoiceListView(ScopedListView):
    model = Invoice
    permission_required = "sales.view_invoice"
    table_class = InvoiceTable
    filterset_class = InvoiceFilter
    template_name = "sales/invoice_list.html"
    page_title = "Invoices"
    allow_add = False  # creation is a full-page flow, not a modal


# --------------------------------------------------------------------------- #
# Invoice editor (multi-line, full page)
# --------------------------------------------------------------------------- #
def _apply_item_price(item, invoice):
    """Derive frozen unit price / kind from the chosen product or service when
    the user didn't type a price explicitly."""
    if item.product_id:
        item.kind = item.KIND_PRODUCT
        item.service = None
        if item.unit_price_lyd in (None, ""):
            item.unit_price_lyd = item.product.selling_price_lyd(invoice.exchange_rate) or Decimal("0")
        item.unit_price_usd = item.product.effective_price_usd
        item.unit_cost_usd = item.product.cost_usd  # freeze cost for exact COGS
    elif item.service_id:
        item.kind = item.KIND_SERVICE
        item.product = None
        item.unit_cost_usd = None  # services carry no goods cost
        if item.unit_price_lyd in (None, ""):
            item.unit_price_lyd = item.service.selling_price_lyd(invoice.exchange_rate) or Decimal("0")
        item.unit_price_usd = item.service.price_usd
    else:
        item.kind = item.KIND_CUSTOM
        if item.unit_price_lyd in (None, ""):
            item.unit_price_lyd = Decimal("0")


class _InvoiceEditorView(LoginRequiredMixin, PermissionRequiredMixin, View):
    raise_exception = True
    template_name = "sales/invoice_form.html"

    def _price_map(self, rate):
        """JSON {kind: {id: lyd_price}} so the editor can auto-fill unit prices."""
        from catalog.models import Product, Service

        products = {
            str(p.pk): float(p.selling_price_lyd(rate) or 0)
            for p in Product.objects.filter(is_active=True)
        }
        services = {
            str(s.pk): float(s.selling_price_lyd(rate) or 0)
            for s in Service.objects.filter(is_active=True)
        }
        return json.dumps({"product": products, "service": services})

    def _context(self, request, form, formset, invoice=None):
        rate = invoice.exchange_rate if invoice else get_current_rate()
        return {
            "form": form,
            "formset": formset,
            "invoice": invoice,
            "current_rate": rate,
            "has_rate": has_configured_rate(),
            "is_edit": invoice is not None,
            "price_map_json": self._price_map(rate),
            # Feeds the customer combobox <datalist> + JS autofill of phone/address.
            # Customers are private, so a rep only ever sees/binds their own book.
            "customers": apply_ownership(
                Customer.objects.filter(is_active=True), self.request.user
            ).order_by("name"),
        }

    def _sync_customer(self, invoice, actor):
        """Bind the invoice to a Customer record for the typed/selected name, and
        persist any new phone/address so future invoices autofill from it.

        - Known customer picked (FK set): fill blank snapshot fields from it, and
          backfill the customer's own blank phone/address from what was typed.
        - New name typed (no FK): reuse an existing same-name customer if one
          exists, else create one — so every customer entered is saved for reuse.
        """
        name = (invoice.customer_name or "").strip()
        customer = invoice.customer if invoice.customer_id else None
        if customer is None and name:
            # Match only within the rep's own (private) customer book; a new name
            # creates a fresh record owned by them.
            customer = (
                apply_ownership(Customer.objects.all(), actor)
                .filter(name__iexact=name)
                .first()
            )
            if customer is None:
                customer = Customer(name=name)
        if customer is None:
            return  # true walk-in with no name at all

        # Snapshot onto the invoice (walk-in fields win if already provided).
        invoice.customer_name = invoice.customer_name or customer.name
        invoice.customer_phone = invoice.customer_phone or customer.phone
        invoice.customer_address = invoice.customer_address or customer.address

        # Backfill the durable customer record without clobbering existing values.
        dirty = customer.pk is None
        if not customer.name and name:
            customer.name, dirty = name, True
        if invoice.customer_phone and not customer.phone:
            customer.phone, dirty = invoice.customer_phone, True
        if invoice.customer_address and not customer.address:
            customer.address, dirty = invoice.customer_address, True
        if dirty:
            customer.save()
        invoice.customer = customer

    def _save(self, request, form, formset, invoice=None):
        with transaction.atomic():
            invoice = form.save(commit=False)
            if invoice.exchange_rate is None:
                invoice.exchange_rate = get_current_rate()
            self._sync_customer(invoice, request.user)
            invoice.save()
            formset.instance = invoice
            items = formset.save(commit=False)
            for obj in items:
                _apply_item_price(obj, invoice)
                obj.save()
            for obj in formset.deleted_objects:
                obj.delete()
            invoice.recalc_totals()
            log_user_action(request, "UPDATE" if invoice.pk else "CREATE", instance=invoice)
        return invoice


class InvoiceCreateView(_InvoiceEditorView):
    permission_required = "sales.add_invoice"

    def get(self, request):
        form = InvoiceForm(user=request.user)
        formset = InvoiceItemFormSet()
        return render(request, self.template_name, self._context(request, form, formset))

    def post(self, request):
        form = InvoiceForm(request.POST, request.FILES, user=request.user)
        formset = InvoiceItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            invoice = self._save(request, form, formset)
            messages.success(request, _("Invoice %(no)s saved as draft.") % {"no": invoice.number})
            return redirect("sales:invoice_detail", pk=invoice.pk)
        return render(request, self.template_name, self._context(request, form, formset))


class InvoiceUpdateView(_InvoiceEditorView):
    permission_required = "sales.change_invoice"

    def _get_invoice(self, pk):
        # Ownership-scoped: a rep can only edit their own/assigned invoices.
        return get_object_or_404(_visible_invoices(self.request.user), pk=pk)

    def get(self, request, pk):
        invoice = self._get_invoice(pk)
        if not invoice.is_editable:
            messages.warning(request, _("Only draft invoices can be edited."))
            return redirect("sales:invoice_detail", pk=invoice.pk)
        form = InvoiceForm(instance=invoice, user=request.user)
        formset = InvoiceItemFormSet(instance=invoice)
        return render(request, self.template_name, self._context(request, form, formset, invoice))

    def post(self, request, pk):
        invoice = self._get_invoice(pk)
        if not invoice.is_editable:
            messages.warning(request, _("Only draft invoices can be edited."))
            return redirect("sales:invoice_detail", pk=invoice.pk)
        form = InvoiceForm(request.POST, request.FILES, instance=invoice, user=request.user)
        formset = InvoiceItemFormSet(request.POST, instance=invoice)
        if form.is_valid() and formset.is_valid():
            invoice = self._save(request, form, formset, invoice)
            messages.success(request, _("Invoice %(no)s updated.") % {"no": invoice.number})
            return redirect("sales:invoice_detail", pk=invoice.pk)
        return render(request, self.template_name, self._context(request, form, formset, invoice))


# --------------------------------------------------------------------------- #
# Invoice detail + lifecycle actions
# --------------------------------------------------------------------------- #
class InvoiceDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Invoice
    permission_required = "sales.view_invoice"
    raise_exception = True
    template_name = "sales/invoice_detail.html"
    context_object_name = "invoice"

    def get_queryset(self):
        return _visible_invoices(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        invoice = self.object
        ctx["items"] = invoice.items.all()
        ctx["payments"] = invoice.payments.all()
        ctx["payment_form"] = PaymentForm()
        # Feeds the deposit combobox <datalist> (search-and-add batches by reference).
        ctx["cash_deposits"] = scope_filtered_queryset(
            CashDeposit.objects.exclude(reference="").order_by("-deposited_at"),
            self.request.user,
        )
        return ctx


class InvoiceIssueView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "sales.issue_invoice"
    raise_exception = True

    def post(self, request, pk):
        invoice = get_object_or_404(_visible_invoices(request.user), pk=pk)
        try:
            issue_invoice(invoice, request.user)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
            return redirect("sales:invoice_detail", pk=pk)
        log_user_action(request, "ISSUE", instance=invoice)
        messages.success(request, _("Invoice %(no)s issued. Stock updated.") % {"no": invoice.number})
        return redirect("sales:invoice_detail", pk=pk)


class InvoiceCancelView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "sales.cancel_invoice"
    raise_exception = True

    def post(self, request, pk):
        invoice = get_object_or_404(_visible_invoices(request.user), pk=pk)
        cancel_invoice(invoice, request.user)
        log_user_action(request, "CANCEL", instance=invoice)
        messages.warning(request, _("Invoice %(no)s cancelled.") % {"no": invoice.number})
        return redirect("sales:invoice_detail", pk=pk)


class InvoicePrintView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Invoice
    permission_required = "sales.view_invoice"
    raise_exception = True
    template_name = "sales/invoice_print.html"
    context_object_name = "invoice"

    def get_queryset(self):
        return _visible_invoices(self.request.user)

    def get_context_data(self, **kwargs):
        from dlux.translations import get_current_language_code

        ctx = super().get_context_data(**kwargs)
        ctx["items"] = self.object.items.all()
        ctx["payments"] = self.object.payments.all()
        lang = get_current_language_code(self.request)
        ctx["doc_lang"] = lang
        ctx["is_rtl"] = lang.startswith("ar")
        return ctx


class PaymentCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "sales.add_payment"
    raise_exception = True

    def post(self, request, pk):
        invoice = get_object_or_404(_visible_invoices(request.user), pk=pk)
        if invoice.status in (Invoice.STATUS_DRAFT, Invoice.STATUS_CANCELLED):
            messages.error(request, _("Issue the invoice before recording payments."))
            return redirect("sales:invoice_detail", pk=pk)
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.invoice = invoice
            self._sync_deposit(request, payment, form.cleaned_data.get("deposit_ref"))
            payment.save()  # recalc_payments + deposit recalc run in Payment.save()
            log_user_action(request, "PAYMENT", instance=invoice)
            messages.success(request, _("Payment recorded."))
        else:
            messages.error(request, _("Could not record payment. Check the amount."))
        return redirect("sales:invoice_detail", pk=pk)

    def _sync_deposit(self, request, payment, reference):
        """Bind the payment to a CashDeposit batch for the typed reference.

        A matched batch (hidden FK already set by JS) is used as-is; a new
        reference creates a pending batch so cash collected on the fly is grouped
        without pre-creating the deposit. The batch amount is auto-summed from its
        payments in ``CashDeposit.recalc_amount`` (triggered by ``Payment.save``).
        """
        if payment.deposit_id:
            return  # existing batch picked from the datalist
        reference = (reference or "").strip()
        if not reference:
            payment.deposit = None
            return
        qs = scope_filtered_queryset(CashDeposit.objects.all(), request.user)
        deposit = qs.filter(reference__iexact=reference).first()
        if deposit is None:
            # amount starts at 0 (NOT NULL) and is set to the batch total by
            # CashDeposit.recalc_amount() the moment payment.save() runs below.
            deposit = CashDeposit(reference=reference, method=payment.method, amount=Decimal("0.00"))
            deposit.save()  # scope / created_by come from the request (ScopedModel)
        payment.deposit = deposit


# --------------------------------------------------------------------------- #
# Dashboard (intended as the system home page)
# --------------------------------------------------------------------------- #
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "sales/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        today = timezone.localdate()
        month_start = today.replace(day=1)
        live_statuses = [Invoice.STATUS_ISSUED, Invoice.STATUS_PARTIAL, Invoice.STATUS_PAID]

        # Role-aware home page. Every panel is both permission-gated (a delivery
        # courier has no view_invoice) and row-scoped: a rep's figures cover only
        # their own sales, a manager (view_all_invoice) sees the whole store.
        ctx["can_view_sales"] = user.has_perm("sales.view_invoice")
        ctx["can_view_deliveries"] = user.has_perm("sales.view_delivery")
        ctx["is_sales_manager"] = user_can_view_all(user, Invoice)

        my_invoices = _visible_invoices(user)
        today_qs = my_invoices.filter(invoice_date=today, status__in=live_statuses)
        month_qs = my_invoices.filter(invoice_date__gte=month_start, status__in=live_statuses)

        ctx["current_rate"] = get_current_rate()
        ctx["has_rate"] = has_configured_rate()
        ctx["latest_rate_row"] = ExchangeRate.objects.order_by("-created_at").first()
        # External reference rates (scraped, cached) shown next to our custom rate:
        # the official CBL rate and the eanlibya black-market rate. Read cache-only
        # here — the web tier is network-isolated; the celery worker (which has
        # egress) does the scraping and populates the shared Redis cache.
        cbl = get_cbl_official_rate(refresh_if_missing=False)
        ctx["cbl_official"] = cbl
        if cbl and cbl.get("average"):
            ctx["cbl_official_rate"] = Decimal(str(cbl["average"]))

        ean = get_ean_black_market_rate(refresh_if_missing=False)
        ctx["ean_market"] = ean
        if ean and ean.get("rate"):
            market = Decimal(str(ean["rate"]))
            ctx["ean_market_rate"] = market
            # Custom pricing tracks the black market, so the meaningful gap is
            # custom vs black-market; fall back to the official rate if EAN is down.
            ctx["rate_gap"] = ctx["current_rate"] - market
        elif ctx.get("cbl_official_rate"):
            ctx["rate_gap"] = ctx["current_rate"] - ctx["cbl_official_rate"]
        ctx["sales_today"] = today_qs.aggregate(t=Sum("total_lyd"))["t"] or Decimal("0")
        ctx["count_today"] = today_qs.count()
        ctx["sales_month"] = month_qs.aggregate(t=Sum("total_lyd"))["t"] or Decimal("0")
        outstanding_qs = my_invoices.filter(status__in=[Invoice.STATUS_ISSUED, Invoice.STATUS_PARTIAL])
        ctx["outstanding"] = (outstanding_qs.aggregate(t=Sum("total_lyd"))["t"] or Decimal("0")) - (
            outstanding_qs.aggregate(t=Sum("amount_paid"))["t"] or Decimal("0")
        )
        ctx["draft_count"] = my_invoices.filter(status=Invoice.STATUS_DRAFT).count()
        ctx["pending_deposits"] = (
            apply_ownership(CashDeposit.objects.all(), user)
            .filter(status=CashDeposit.STATUS_PENDING)
            .count()
        )
        ctx["recent_invoices"] = my_invoices.order_by("-created_at")[:8]

        # Delivery board — the courier's own open jobs (or all, for a dispatcher).
        if ctx["can_view_deliveries"]:
            open_deliveries = apply_ownership(
                Delivery.objects.filter(status__in=Delivery.OPEN_STATUSES), user
            ).order_by("scheduled_date", "-created_at")
            ctx["open_deliveries"] = open_deliveries[:8]
            ctx["open_delivery_count"] = open_deliveries.count()

        # Low-stock is a catalog concern — only for users who can see products.
        if user.has_perm("catalog.view_product"):
            from catalog.models import Product

            low = [p for p in Product.objects.filter(track_stock=True, is_active=True) if p.is_low_stock]
            ctx["low_stock"] = low[:8]
            ctx["low_stock_count"] = len(low)
        return ctx


# --------------------------------------------------------------------------- #
# Sales reporting (+ XLSX export)
# --------------------------------------------------------------------------- #
class SalesReportView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    permission_required = "sales.view_sales_report"
    raise_exception = True
    template_name = "sales/report.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        date_from, date_to = parse_window(
            self.request.GET.get("date_from"), self.request.GET.get("date_to")
        )
        ctx["report"] = build_sales_report(date_from, date_to, self.request.user)
        ctx["date_from"] = date_from
        ctx["date_to"] = date_to
        return ctx


class FinancialReportView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Whole-store fiscal-year P&L (owner/manager). Not row-scoped — its own
    permission gates it (COGS / margins / capital-in-stock are sensitive)."""

    permission_required = "sales.view_financial_report"
    raise_exception = True
    template_name = "sales/financial_report.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        years = available_fiscal_years()
        try:
            year = int(self.request.GET.get("year", ""))
        except (TypeError, ValueError):
            year = years[0]
        if year not in years:
            year = years[0]
        date_from, date_to = fiscal_year_window(year)
        ctx["report"] = build_financial_report(date_from, date_to)
        ctx["year"] = year
        ctx["years"] = years
        return ctx


class SalesReportExportView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "sales.view_sales_report"
    raise_exception = True

    def get(self, request):
        date_from, date_to = parse_window(request.GET.get("date_from"), request.GET.get("date_to"))
        report = build_sales_report(date_from, date_to, request.user)
        content = build_sales_report_xlsx(report)
        log_user_action(request, "EXPORT", model_name="Sales Report")
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="sales_report_{date_from}_{date_to}.xlsx"'
        )
        return response
