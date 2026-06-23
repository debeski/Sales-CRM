from django import forms
from django.forms import inlineformset_factory

from dlux.utils import set_field_attrs

from .models import Customer, Invoice, InvoiceItem, Payment


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["name", "phone", "address", "notes", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_field_attrs(self)


class InvoiceForm(forms.ModelForm):
    """Invoice header. The frozen ``exchange_rate`` is assigned by the view, not
    typed by the user."""

    class Meta:
        model = Invoice
        fields = [
            "customer", "customer_name", "customer_phone", "customer_address",
            "invoice_date", "discount_percent", "discount_amount", "notes",
        ]
        widgets = {"invoice_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].required = False
        set_field_attrs(self)


class InvoiceItemForm(forms.ModelForm):
    class Meta:
        model = InvoiceItem
        fields = ["kind", "product", "service", "description", "unit_price_lyd", "quantity"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Price may be left blank to auto-fill from the selected product/service.
        self.fields["unit_price_lyd"].required = False
        self.fields["description"].required = False
        set_field_attrs(self, inline_labels=True)


# Inline formset that powers the multi-line invoice editor.
InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    extra=1,
    can_delete=True,
)


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["amount", "method", "paid_at", "deposit", "notes"]
        widgets = {"paid_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["deposit"].required = False
        set_field_attrs(self)
