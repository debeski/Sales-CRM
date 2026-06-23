from dlux.tables import DluxTable

from common.i18n import t

from .models import CashDeposit, ExchangeRate


class ExchangeRateTable(DluxTable):
    class Meta(DluxTable.Meta):
        model = ExchangeRate
        fields = ("rate", "source", "note", "created_by", "created_at")
        dlux_actions = True

    def render_source(self, record):
        return t(f"source_{record.source}", record.get_source_display())


class CashDepositTable(DluxTable):
    class Meta(DluxTable.Meta):
        model = CashDeposit
        fields = ("amount", "method", "deposited_at", "status", "created_by", "created_at")
        dlux_actions = True

    def render_method(self, record):
        return t(f"method_{record.method}", record.get_method_display())

    def render_status(self, record):
        return t(f"status_{record.status}", record.get_status_display())
