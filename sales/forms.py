from django import forms
from django.forms import inlineformset_factory

from dlux.translations import get_strings
from dlux.utils import set_field_attrs

from common.forms import translate_choice_fields, translate_help_text

from .models import Customer, Invoice, InvoiceItem, Payment


class CustomerForm(forms.ModelForm):
    # Reload the parent list page after a successful dynamic-modal save.
    refresh_parent = True

    class Meta:
        model = Customer
        fields = ["name", "phone", "address", "notes", "is_active"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_field_attrs(self)
        translate_help_text(self)


class InvoiceForm(forms.ModelForm):
    """Invoice header. The frozen ``exchange_rate`` is assigned by the view, not
    typed by the user."""

    class Meta:
        model = Invoice
        fields = [
            "customer", "customer_name", "customer_phone", "customer_address",
            "invoice_date", "discount_percent", "discount_amount", "notes",
        ]
        widgets = {
            "invoice_date": forms.DateInput(attrs={"type": "date"}),
            # The FK is a hidden companion to the visible name combobox; JS fills
            # it with the matched customer's pk (blank for a brand-new walk-in).
            "customer": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].required = False
        # Single search-and-add combobox: a text input backed by <datalist> of
        # existing customers (rendered in the template). autocomplete is off so
        # the datalist — not the browser history — drives suggestions.
        self.fields["customer_name"].widget.attrs.update({
            "list": "customer-datalist",
            "autocomplete": "off",
            "data-customer-input": "1",
        })
        set_field_attrs(self)
        translate_help_text(self)


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
        translate_help_text(self)


# Inline formset that powers the multi-line invoice editor.
InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    extra=1,
    can_delete=True,
)


class PaymentForm(forms.ModelForm):
    # Search-and-add combobox for the optional cash-deposit batch, mirroring the
    # customer field: a <datalist>-backed text input whose value is a deposit
    # reference. JS fills the hidden ``deposit`` FK when the text matches an
    # existing batch; a new reference creates one on save (see _sync_deposit).
    deposit_ref = forms.CharField(required=False)

    class Meta:
        model = Payment
        # paid_at is intentionally excluded: it's set from the model default
        # (timezone.now) on save. Including it made the inline quick-pay form —
        # which only renders amount/method/deposit — fail "paid_at is required".
        fields = ["amount", "method", "deposit", "notes"]
        widgets = {"deposit": forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["deposit"].required = False
        strings = get_strings()
        self.fields["deposit_ref"].label = strings.get("label_payment_deposit", "Cash Deposit")
        if self.instance.pk and self.instance.deposit_id:
            self.fields["deposit_ref"].initial = self.instance.deposit.reference
        self.fields["deposit_ref"].widget.attrs.update({
            "list": "deposit-datalist",
            "autocomplete": "off",
            "data-deposit-input": "1",
            "placeholder": strings.get("ui_deposit_search", "Search or add a deposit…"),
        })
        set_field_attrs(self)
        translate_choice_fields(self)
        translate_help_text(self)
