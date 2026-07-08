from django import forms

from dlux.translations import get_strings
from dlux.utils import set_field_attrs

from common.forms import build_grid_helper, translate_choice_fields, translate_help_text

from .models import CashDeposit, ExchangeRate


class ExchangeRateForm(forms.ModelForm):
    # Reload the parent list page after a successful dynamic-modal save.
    refresh_parent = True

    class Meta:
        model = ExchangeRate
        fields = ["rate", "source", "note"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_field_attrs(self)
        translate_choice_fields(self)
        translate_help_text(self)
        build_grid_helper(self, [("rate", "source"), ("note",)])


class CashDepositForm(forms.ModelForm):
    refresh_parent = True

    class Meta:
        model = CashDeposit
        # status / confirmation are driven by privileged actions, never the form.
        fields = ["amount", "method", "deposited_at", "reference", "notes"]
        widgets = {"deposited_at": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # When this deposit carries invoice payments its amount is the auto-summed
        # batch total — lock the field so it isn't hand-edited out of sync.
        if self.instance.pk and self.instance.payments.exists():
            self.fields["amount"].disabled = True
            self.fields["amount"].help_text = get_strings().get(
                "help_deposit_amount_auto", "Auto-calculated from linked invoice payments."
            )
        set_field_attrs(self)
        translate_choice_fields(self)
        # Runs after the auto-sum note above; there is no help_cashdeposit_amount
        # key, so that per-instance note is preserved.
        translate_help_text(self)
        build_grid_helper(self, [("amount", "method"), ("deposited_at", "reference"), ("notes",)])
