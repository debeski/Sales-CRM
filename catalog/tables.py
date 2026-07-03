import django_tables2 as tables
from django.utils.html import format_html

from dlux.tables import DluxTable

from common.i18n import t

from .models import Category, Product, Service, StockMovement


def _fmt_lyd(value):
    if value is None:
        return "—"
    return f"{value:,.2f}"


class CategoryTable(DluxTable):
    class Meta(DluxTable.Meta):
        model = Category
        fields = ("name", "is_active", "created_at")
        dlux_actions = True


class ProductTable(DluxTable):
    price_lyd = tables.Column(
        empty_values=(), verbose_name="Price (LYD)", orderable=False
    )
    stock_qty = tables.Column(verbose_name="Stock")

    class Meta(DluxTable.Meta):
        model = Product
        fields = ("name", "sku", "barcode", "category", "unit", "stock_qty", "price_lyd", "is_active")
        dlux_actions = True

    def render_price_lyd(self, record):
        return _fmt_lyd(record.selling_price_lyd())

    def render_unit(self, record):
        return t(f"unit_{record.unit}", record.get_unit_display())

    def render_stock_qty(self, record):
        if not record.track_stock:
            # Django 6.0's format_html requires a placeholder arg; pass the dash.
            return format_html('<span class="text-muted">{}</span>', "—")
        if record.is_low_stock:
            return format_html('<span class="text-danger fw-semibold">{}</span>', f"{record.stock_qty:g}")
        return f"{record.stock_qty:g}"


class ServiceTable(DluxTable):
    price_lyd = tables.Column(empty_values=(), verbose_name="Price (LYD)", orderable=False)

    class Meta(DluxTable.Meta):
        model = Service
        fields = ("name", "service_type", "price_lyd", "is_active")
        dlux_actions = True

    def render_price_lyd(self, record):
        price = record.selling_price_lyd()
        return _fmt_lyd(price) if price is not None else t("ui_per_job", "Per job")

    def render_service_type(self, record):
        return t(f"svctype_{record.service_type}", record.get_service_type_display())


class StockMovementTable(DluxTable):
    class Meta(DluxTable.Meta):
        model = StockMovement
        fields = ("product", "movement_type", "quantity", "reference", "created_by", "created_at")
        dlux_actions = True

    def render_movement_type(self, record):
        return t(f"mtype_{record.movement_type}", record.get_movement_type_display())
