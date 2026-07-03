from django import forms

from dlux.utils import set_field_attrs

from common.forms import translate_choice_fields

from .models import Category, Product, Service, StockMovement


class CategoryForm(forms.ModelForm):
    # Reload the parent list page after a successful dynamic-modal save.
    refresh_parent = True

    class Meta:
        model = Category
        fields = ["name", "description", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_field_attrs(self)


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
        self.fields["sku"].help_text = "Leave blank to auto-generate."
        set_field_attrs(self)
        translate_choice_fields(self)


class ServiceForm(forms.ModelForm):
    refresh_parent = True

    class Meta:
        model = Service
        fields = ["name", "service_type", "description", "price_usd", "price_lyd_override", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_field_attrs(self)
        translate_choice_fields(self)


class StockMovementForm(forms.ModelForm):
    refresh_parent = True

    class Meta:
        model = StockMovement
        fields = ["product", "movement_type", "quantity", "reason", "reference"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_field_attrs(self)
        translate_choice_fields(self)
