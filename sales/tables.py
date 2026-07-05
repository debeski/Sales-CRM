import django_tables2 as tables
from django.urls import reverse
from django.utils.html import format_html

from dlux.tables import DluxTable

from common.i18n import t

from .models import Customer, Delivery, Invoice, Payment

_STATUS_BADGE = {
    "draft": "bg-secondary",
    "issued": "bg-info text-dark",
    "partial": "bg-warning text-dark",
    "paid": "bg-success",
    "cancelled": "bg-danger",
}

_DELIVERY_BADGE = {
    "pending": "bg-secondary",
    "assigned": "bg-info text-dark",
    "out": "bg-warning text-dark",
    "delivered": "bg-success",
    "failed": "bg-danger",
    "cancelled": "bg-dark",
}


def _user_label(user):
    if user is None:
        return "—"
    return (user.get_full_name() or user.get_username()) if hasattr(user, "get_username") else str(user)


class InvoiceTable(DluxTable):
    number = tables.Column(verbose_name="Invoice No.")
    customer = tables.Column(empty_values=(), verbose_name="Customer", orderable=False)
    salesperson = tables.Column(verbose_name="Salesperson")
    status = tables.Column(verbose_name="Status")
    total_lyd = tables.Column(verbose_name="Total (LYD)")
    balance = tables.Column(empty_values=(), verbose_name="Balance (LYD)", orderable=False)

    class Meta(DluxTable.Meta):
        model = Invoice
        fields = ("number", "customer", "salesperson", "invoice_date", "status", "total_lyd", "balance")
        dlux_actions = False  # invoices use full-page flows, not modal CRUD

    def render_salesperson(self, record):
        return _user_label(record.salesperson)

    def render_number(self, record):
        return format_html(
            '<a href="{}" class="fw-semibold text-decoration-none">{}</a>',
            reverse("sales:invoice_detail", args=[record.pk]),
            record.number or "—",
        )

    def render_customer(self, record):
        return record.display_customer

    def render_status(self, record):
        return format_html(
            '<span class="badge rounded-pill {}">{}</span>',
            _STATUS_BADGE.get(record.status, "bg-secondary"),
            t(f"status_{record.status}", record.get_status_display()),
        )

    def render_total_lyd(self, record):
        return f"{record.total_lyd:,.2f}"

    def render_balance(self, record):
        bal = record.balance_due
        css = "text-danger fw-semibold" if bal > 0 else "text-success"
        return format_html('<span class="{}">{}</span>', css, f"{bal:,.2f}")


class CustomerTable(DluxTable):
    class Meta(DluxTable.Meta):
        model = Customer
        fields = ("name", "phone", "address", "is_active", "created_at")
        dlux_actions = True


class PaymentTable(DluxTable):
    invoice = tables.Column(verbose_name="Invoice")
    amount = tables.Column(verbose_name="Amount (LYD)")

    class Meta(DluxTable.Meta):
        model = Payment
        fields = ("invoice", "amount", "method", "paid_at", "created_by")
        dlux_actions = False

    def render_invoice(self, record):
        return format_html(
            '<a href="{}" class="text-decoration-none">{}</a>',
            reverse("sales:invoice_detail", args=[record.invoice_id]),
            record.invoice.number,
        )

    def render_amount(self, record):
        return f"{record.amount:,.2f}"

    def render_method(self, record):
        return t(f"method_{record.method}", record.get_method_display())


class DeliveryTable(DluxTable):
    recipient = tables.Column(verbose_name="Recipient")
    status = tables.Column(verbose_name="Status")
    assigned_to = tables.Column(verbose_name="Assigned To")

    class Meta(DluxTable.Meta):
        model = Delivery
        fields = ("recipient", "address", "status", "assigned_to", "scheduled_date", "created_at")
        dlux_actions = True

    def render_status(self, record):
        return format_html(
            '<span class="badge rounded-pill {}">{}</span>',
            _DELIVERY_BADGE.get(record.status, "bg-secondary"),
            t(f"delivery_status_{record.status}", record.get_status_display()),
        )

    def render_assigned_to(self, record):
        return _user_label(record.assigned_to)
