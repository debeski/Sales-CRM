from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import DetailView, TemplateView

from dlux.utils import log_user_action

from common.views import ScopedListView
from finance.services import get_current_rate, usd_to_lyd

from .filters import CategoryFilter, ProductFilter, ServiceFilter, StockMovementFilter, StockTakeFilter
from .models import Category, Product, Service, StockMovement, StockTake, StockTakeLine
from .tables import CategoryTable, ProductTable, ServiceTable, StockMovementTable, StockTakeTable


class CategoryListView(ScopedListView):
    model = Category
    permission_required = "catalog.view_category"
    table_class = CategoryTable
    filterset_class = CategoryFilter
    page_title_key = "page_categories"


class ProductListView(ScopedListView):
    model = Product
    permission_required = "catalog.view_product"
    table_class = ProductTable
    filterset_class = ProductFilter
    page_title_key = "page_products"
    page_subtitle_key = "page_products_sub"
    # Live sync of the cost/markup/USD/LYD price fields in the create-edit modal.
    extra_scripts = ("catalog/js/price_sync.js",)


class ServiceListView(ScopedListView):
    model = Service
    permission_required = "catalog.view_service"
    table_class = ServiceTable
    filterset_class = ServiceFilter
    page_title_key = "page_services"
    page_subtitle_key = "page_services_sub"
    extra_scripts = ("catalog/js/price_sync.js",)


class StockMovementListView(ScopedListView):
    model = StockMovement
    permission_required = "catalog.view_stockmovement"
    table_class = StockMovementTable
    filterset_class = StockMovementFilter
    page_title_key = "page_stock_movements"
    page_subtitle_key = "page_stock_movements_sub"


# --------------------------------------------------------------------------- #
# Stock take (physical inventory count) + inventory valuation
# --------------------------------------------------------------------------- #
def _parse_qty(raw):
    """Blank -> None (uncounted); a valid number -> Decimal; junk -> None."""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        return None


class StockTakeListView(ScopedListView):
    model = StockTake
    permission_required = "catalog.view_stocktake"
    table_class = StockTakeTable
    filterset_class = StockTakeFilter
    template_name = "catalog/stock_take_list.html"  # adds New-count + Valuation buttons
    page_title_key = "page_stock_takes"
    allow_add = False  # created via the full-page count flow, not a modal


class StockTakeCreateView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Full-page count sheet: every active tracked product with an input for the
    physical count. Submitting snapshots the system quantity and creates the take
    (status = open); adjustments are posted later from the detail page."""

    permission_required = "catalog.add_stocktake"
    raise_exception = True
    template_name = "catalog/stock_take_form.html"

    def _products(self):
        return Product.objects.filter(is_active=True, track_stock=True).order_by("name")

    def get(self, request):
        return render(request, self.template_name, {"products": self._products()})

    def post(self, request):
        products = list(self._products())
        with transaction.atomic():
            take = StockTake(notes=request.POST.get("notes", ""))  # count_date defaults to today
            take.save()
            for p in products:
                StockTakeLine.objects.create(
                    stock_take=take,
                    product=p,
                    system_qty=p.stock_qty,
                    counted_qty=_parse_qty(request.POST.get(f"count_{p.pk}")),
                )
            log_user_action(request, "CREATE", instance=take)
        messages.success(request, _("Stock take %(no)s saved.") % {"no": take.number})
        return redirect("catalog:stock_take_detail", pk=take.pk)


class StockTakeDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = StockTake
    permission_required = "catalog.view_stocktake"
    raise_exception = True
    template_name = "catalog/stock_take_detail.html"
    context_object_name = "take"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        take = self.object
        rate = get_current_rate()
        lines = list(take.lines.select_related("product"))
        for ln in lines:
            ln.variance_lyd = ln.variance_value_lyd(rate)
        ctx["lines"] = lines
        ctx["discrepancy_count"] = len(take.discrepancy_lines)
        ctx["total_variance_lyd"] = take.total_variance_value_lyd
        ctx["can_apply"] = take.is_open and self.request.user.has_perm("catalog.apply_stocktake")
        return ctx


class StockTakeApplyView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "catalog.apply_stocktake"
    raise_exception = True

    def post(self, request, pk):
        take = get_object_or_404(StockTake, pk=pk)
        try:
            take.apply(request.user)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
            return redirect("catalog:stock_take_detail", pk=pk)
        log_user_action(request, "UPDATE", instance=take)
        messages.success(request, _("Stock take %(no)s applied. Stock adjusted.") % {"no": take.number})
        return redirect("catalog:stock_take_detail", pk=pk)


class InventoryValuationView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """What the stock on hand is worth right now: Σ(stock_qty × unit cost)."""

    permission_required = "catalog.view_inventory_valuation"
    raise_exception = True
    template_name = "catalog/inventory_valuation.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        rate = get_current_rate()
        rows = []
        total_usd = Decimal("0.00")
        for p in Product.objects.filter(is_active=True, track_stock=True).order_by("name"):
            value_usd = (p.stock_qty or Decimal("0")) * (p.cost_usd or Decimal("0"))
            total_usd += value_usd
            rows.append({
                "product": p,
                "stock_qty": p.stock_qty,
                "cost_usd": p.cost_usd,
                "value_usd": value_usd,
                "value_lyd": usd_to_lyd(value_usd, rate),
            })
        ctx["rows"] = rows
        ctx["total_usd"] = total_usd
        ctx["total_lyd"] = usd_to_lyd(total_usd, rate)
        ctx["rate"] = rate
        ctx["item_count"] = len(rows)
        return ctx
