"""
Invoice lifecycle operations that touch more than one row/app.

Kept out of the model so the cross-app side effects (stock ledger, rate snapshot)
are explicit and wrapped in a single transaction.
"""
from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from catalog.models import StockMovement
from finance.models import ExchangeRate

from .models import Invoice


@transaction.atomic
def issue_invoice(invoice, user):
    """Move a draft invoice to *issued*: snapshot the rate record and draw down
    stock for every product line. Idempotent — only acts on drafts."""
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if invoice.status != Invoice.STATUS_DRAFT:
        return invoice
    if not invoice.items.exists():
        raise ValidationError(_("Cannot issue an invoice with no items."))

    # Stock guard: aggregate demand per tracked product (a product may appear on
    # several lines) and refuse to issue if any would go negative.
    needs = defaultdict(lambda: Decimal("0"))
    products = {}
    for item in invoice.items.select_related("product"):
        if item.kind == item.KIND_PRODUCT and item.product_id and item.product.track_stock:
            needs[item.product_id] += item.quantity
            products[item.product_id] = item.product

    shortages = [
        _("%(name)s (need %(need)s, have %(have)s)")
        % {"name": products[pid].name, "need": qty, "have": products[pid].stock_qty}
        for pid, qty in needs.items()
        if products[pid].stock_qty < qty
    ]
    if shortages:
        raise ValidationError(_("Insufficient stock to issue: ") + "; ".join(shortages))

    invoice.exchange_rate_obj = ExchangeRate.objects.order_by("-created_at").first()

    for item in invoice.items.select_related("product"):
        if item.kind == item.KIND_PRODUCT and item.product_id and item.product.track_stock:
            StockMovement.objects.create(
                product=item.product,
                movement_type=StockMovement.TYPE_OUT,
                quantity=item.quantity,
                reason=_("Sold on invoice %(no)s") % {"no": invoice.number},
                reference=invoice.number,
            )

    invoice.status = Invoice.STATUS_ISSUED
    invoice.issued_at = timezone.now()
    invoice.save(update_fields=["status", "issued_at", "exchange_rate_obj", "updated_at"])
    invoice.recalc_payments()
    return invoice


@transaction.atomic
def cancel_invoice(invoice, user):
    """Cancel an invoice and restore any stock it had drawn down."""
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if invoice.status == Invoice.STATUS_CANCELLED:
        return invoice

    was_issued = invoice.status in (
        Invoice.STATUS_ISSUED, Invoice.STATUS_PARTIAL, Invoice.STATUS_PAID,
    )
    if was_issued:
        for item in invoice.items.select_related("product"):
            if item.kind == item.KIND_PRODUCT and item.product_id and item.product.track_stock:
                StockMovement.objects.create(
                    product=item.product,
                    movement_type=StockMovement.TYPE_IN,
                    quantity=item.quantity,
                    reason=_("Cancelled invoice %(no)s") % {"no": invoice.number},
                    reference=invoice.number,
                )

    invoice.status = Invoice.STATUS_CANCELLED
    invoice.save(update_fields=["status", "updated_at"])
    return invoice
