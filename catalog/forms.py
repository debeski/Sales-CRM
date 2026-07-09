from decimal import Decimal

from django import forms
from django.forms import formset_factory

from dlux.forms import _build_archive_file_widget
from dlux.translations import get_strings
from dlux.utils import set_field_attrs

from common.forms import build_grid_helper, translate_choice_fields, translate_help_text
from finance.services import get_current_rate

from .models import Category, Product, PurchaseInvoice, Service, StockMovement, Supplier


def _use_dlux_image_widget(form, field_name="image"):
    """Swap the plain file input for dlux's rich archive file field (drag-drop
    card + thumbnail preview + upload button). ``accept="image/*"`` is preserved
    on the underlying input, so a phone still offers camera-or-gallery. Call this
    AFTER set_field_attrs so the captured label is already translated; the card
    renders its own label, so the field's crispy label is cleared to avoid a
    duplicate. ``show_scan`` is left off — that button is dlux's desktop TWAIN
    scanner (ScanLink), not the mobile camera."""
    field = form.fields.get(field_name)
    if field is None:
        return
    field.widget = _build_archive_file_widget(
        field_label=field.label, show_scan=False, attrs={"accept": "image/*"}
    )
    field.label = ""


def _use_dlux_document_widget(form, field_name="attachment"):
    """Rich file input for supporting purchase-invoice scans/photos/PDFs."""
    field = form.fields.get(field_name)
    if field is None:
        return
    field.widget = _build_archive_file_widget(
        field_label=field.label,
        show_scan=True,
        attrs={"accept": "image/*,application/pdf"},
    )
    field.label = ""


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
        build_grid_helper(self, [("name", "is_active"), "description"])


class SupplierForm(forms.ModelForm):
    refresh_parent = True

    class Meta:
        model = Supplier
        fields = ["name", "phone", "address", "notes", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_field_attrs(self)
        translate_help_text(self)
        build_grid_helper(self, [("name", "phone"), ("address", "is_active"), ("notes",)])


class ProductForm(forms.ModelForm):
    refresh_parent = True

    class Meta:
        model = Product
        # stock_qty is intentionally excluded: stock is driven by StockMovement so
        # the ledger stays authoritative. Use a "Stock In" movement to seed quantity.
        fields = [
            "name", "sku", "category", "barcode", "image", "unit", "description",
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
        _use_dlux_image_widget(self)
        build_grid_helper(self, [
            ("name", "sku"),
            ("category", "unit"),
            ("barcode",),
            ("image",),
            ("cost_usd", "markup_percent", "price_usd"),
            ("price_lyd_override", "reorder_level"),
            ("track_stock", "is_active"),
            ("description",),
        ])


class ServiceForm(forms.ModelForm):
    refresh_parent = True

    class Meta:
        model = Service
        fields = ["name", "service_type", "image", "description", "price_usd", "price_lyd_override", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["price_usd"].widget.attrs["data-price-usd"] = "1"
        self.fields["price_lyd_override"].widget.attrs["data-price-lyd"] = "1"
        _tag_lyd_field(self, "price_lyd_override")
        set_field_attrs(self)
        translate_choice_fields(self)
        translate_help_text(self)
        self.fields["price_lyd_override"].widget.attrs.pop("placeholder", None)
        _use_dlux_image_widget(self)
        build_grid_helper(self, [
            ("name", "service_type"),
            ("image",),
            ("price_usd", "price_lyd_override", "is_active"),
            ("description",),
        ])


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
        build_grid_helper(self, [("product", "movement_type"), ("quantity", "reference"), ("reason",)])


class PurchaseInvoiceForm(forms.ModelForm):
    """Purchase invoice header. The visible supplier name is a datalist-backed
    combobox; the hidden FK is filled when the typed supplier already exists."""

    class Meta:
        model = PurchaseInvoice
        fields = [
            "supplier", "supplier_name", "supplier_phone", "supplier_address",
            "invoice_date", "attachment", "notes",
        ]
        widgets = {
            "invoice_date": forms.DateInput(attrs={"type": "date"}),
            "supplier": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["supplier"].required = False
        self.fields["supplier_name"].required = True
        self.fields["supplier_name"].widget.attrs.update({
            "list": "supplier-datalist",
            "autocomplete": "off",
            "data-supplier-input": "1",
        })
        set_field_attrs(self)
        translate_help_text(self)
        _use_dlux_document_widget(self)
        build_grid_helper(self, [
            ("supplier_name", "supplier_phone"),
            ("supplier_address", "invoice_date"),
            ("notes",),
            ("attachment",),
        ])


class OpeningStockLineForm(forms.Form):
    """One row of the one-time opening-stock grid. Deliberately **not** a
    ModelForm — a row spans creating/reusing a ``Product`` and posting a Stock In
    ``StockMovement``, both done in the view; there is no opening-stock model.
    The visible ``name`` doubles as a new-or-existing product combobox: JS matches
    it against existing products, fills the hidden ``product`` id (blank = a
    brand-new item), and autofills cost/markup/price from the product map."""

    product = forms.IntegerField(required=False, widget=forms.HiddenInput())
    name = forms.CharField(required=False, max_length=200)
    category = forms.ModelChoiceField(queryset=Category.objects.all(), required=False)
    unit = forms.ChoiceField(choices=Product.UNIT_CHOICES, initial=Product.UNIT_PIECE)
    barcode = forms.CharField(required=False, max_length=64)
    cost_usd = forms.DecimalField(required=False, min_value=0, max_digits=12, decimal_places=2, initial=Decimal("0"))
    markup_percent = forms.DecimalField(required=False, min_value=0, max_digits=6, decimal_places=2, initial=Decimal("0"))
    price_usd = forms.DecimalField(required=False, min_value=0, max_digits=12, decimal_places=2, initial=Decimal("0"))
    price_lyd_override = forms.DecimalField(required=False, min_value=0, max_digits=14, decimal_places=2)
    quantity = forms.DecimalField(required=False, min_value=0, max_digits=12, decimal_places=2, initial=Decimal("0"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from common.i18n import t

        s = get_strings()
        labels = {
            "name": s.get("label_product_name", "Name"),
            "category": s.get("label_product_category", "Category"),
            "unit": s.get("label_product_unit", "Unit"),
            "barcode": s.get("label_product_barcode", "Barcode"),
            "cost_usd": s.get("label_product_cost_usd", "Import Cost (USD)"),
            "markup_percent": s.get("label_product_markup_percent", "Markup %"),
            "price_usd": s.get("label_product_price_usd", "Selling Price (USD)"),
            "price_lyd_override": s.get("label_product_price_lyd_override", "Manual LYD Price"),
            "quantity": s.get("label_openingstockline_quantity", "Qty in Storage"),
        }
        for name, label in labels.items():
            self.fields[name].label = label
        # Translate the unit choices to the active language.
        self.fields["unit"].choices = [(v, t(f"unit_{v}", lbl)) for v, lbl in Product.UNIT_CHOICES]
        # Combobox + price-sync hooks (same data-* the invoice/product forms use).
        self.fields["name"].widget.attrs.update({
            "list": "product-datalist", "autocomplete": "off", "data-product-input": "1",
        })
        self.fields["cost_usd"].widget.attrs["data-price-cost"] = "1"
        self.fields["markup_percent"].widget.attrs["data-price-markup"] = "1"
        self.fields["price_usd"].widget.attrs["data-price-usd"] = "1"
        self.fields["price_lyd_override"].widget.attrs["data-price-lyd"] = "1"
        self.fields["price_lyd_override"].widget.attrs["data-usd-rate"] = str(get_current_rate())
        # Self-contained Bootstrap styling (no ModelForm, so set_field_attrs doesn't apply).
        for name, field in self.fields.items():
            w = field.widget
            if isinstance(w, forms.HiddenInput):
                continue
            if isinstance(w, forms.Select):
                w.attrs.setdefault("class", "form-select form-select-sm")
            else:
                w.attrs.setdefault("class", "form-control form-control-sm")
                if field.label:
                    w.attrs.setdefault("placeholder", field.label)


class PurchaseInvoiceLineForm(OpeningStockLineForm):
    """Purchase-line row with the same product autofill/price-sync controls as
    Opening Stock, but a filled row must carry a positive purchased quantity."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        s = get_strings()
        self.fields["quantity"].label = s.get("label_purchaseinvoiceline_quantity", "Qty Purchased")
        self.fields["quantity"].widget.attrs["placeholder"] = self.fields["quantity"].label

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("DELETE"):
            return cleaned
        has_data = any(
            cleaned.get(name)
            for name in (
                "product", "name", "category", "barcode", "cost_usd", "markup_percent",
                "price_usd", "price_lyd_override", "quantity",
            )
        )
        if not has_data:
            return cleaned
        if not (cleaned.get("name") or "").strip():
            self.add_error("name", get_strings().get("ui_required_product_name", "Enter a product name."))
        if not cleaned.get("quantity") or cleaned["quantity"] <= 0:
            self.add_error("quantity", get_strings().get("ui_required_positive_quantity", "Enter a quantity greater than zero."))
        return cleaned


# Plain formset powering the multi-row opening-stock grid (add-row JS mirrors the
# invoice item grid). Fully-empty rows are ignored; blank-name rows are dropped
# in the view.
OpeningStockLineFormSet = formset_factory(OpeningStockLineForm, extra=1, can_delete=True)
PurchaseInvoiceLineFormSet = formset_factory(PurchaseInvoiceLineForm, extra=1, can_delete=True)
