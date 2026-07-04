from django import forms

from dlux.utils import set_field_attrs

from common.forms import translate_choice_fields, translate_help_text
from finance.services import get_current_rate

from .models import Category, Product, Service, StockMovement


def _tag_lyd_field(form, field_name):
    """Expose the live USD→LYD rate on a widget so the price-sync JS can preview
    the LYD selling price as the user types (see catalog/js/price_sync.js)."""
    if field_name in form.fields:
        form.fields[field_name].widget.attrs["data-usd-rate"] = str(get_current_rate())


class CategoryForm(forms.ModelForm):
    # Reload the parent list page after a successful dynamic-modal save.
    refresh_parent = True

    class Meta:
        model = Category
        fields = ["name", "description", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_field_attrs(self)
        translate_help_text(self)


class ProductForm(forms.ModelForm):
    refresh_parent = True

    class Meta:
        model = Product
        # stock_qty is intentionally excluded: stock is driven by StockMovement so
        # the ledger stays authoritative. Use a "Stock In" movement to seed quantity.
        fields = [
            "name", "sku", "category", "barcode", "unit", "description",
            "cost_usd", "markup_percent", "price_usd", "price_lyd_override",
            "track_stock", "reorder_level", "is_active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sku"].required = False
        # Data hooks the price-sync JS keys off (see catalog/js/price_sync.js).
        self.fields["cost_usd"].widget.attrs["data-price-cost"] = "1"
        self.fields["markup_percent"].widget.attrs["data-price-markup"] = "1"
        self.fields["price_usd"].widget.attrs["data-price-usd"] = "1"
        self.fields["price_lyd_override"].widget.attrs["data-price-lyd"] = "1"
        _tag_lyd_field(self, "price_lyd_override")
        set_field_attrs(self)
        translate_choice_fields(self)
        translate_help_text(self)
        # set_field_attrs seeds a placeholder from the label; the JS repurposes the
        # LYD field's placeholder to show the live derived price, so clear it here.
        self.fields["price_lyd_override"].widget.attrs.pop("placeholder", None)


class ServiceForm(forms.ModelForm):
    refresh_parent = True

    class Meta:
        model = Service
        fields = ["name", "service_type", "description", "price_usd", "price_lyd_override", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["price_usd"].widget.attrs["data-price-usd"] = "1"
        self.fields["price_lyd_override"].widget.attrs["data-price-lyd"] = "1"
        _tag_lyd_field(self, "price_lyd_override")
        set_field_attrs(self)
        translate_choice_fields(self)
        translate_help_text(self)
        self.fields["price_lyd_override"].widget.attrs.pop("placeholder", None)


class StockMovementForm(forms.ModelForm):
    refresh_parent = True

    class Meta:
        model = StockMovement
        fields = ["product", "movement_type", "quantity", "reason", "reference"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_field_attrs(self)
        translate_choice_fields(self)
        translate_help_text(self)
