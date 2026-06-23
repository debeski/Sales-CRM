from django import forms

from dlux.utils import set_field_attrs

from .models import CashDeposit, ExchangeRate


class ExchangeRateForm(forms.ModelForm):
    class Meta:
        model = ExchangeRate
        fields = ["rate", "source", "note"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_field_attrs(self)


class CashDepositForm(forms.ModelForm):
    class Meta:
        model = CashDeposit
        # status / confirmation are driven by privileged actions, never the form.
        fields = ["amount", "method", "deposited_at", "reference", "notes"]
        widgets = {"deposited_at": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_field_attrs(self)
