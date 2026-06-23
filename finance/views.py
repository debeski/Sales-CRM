from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext as _
from django.views import View

from dlux.utils import log_user_action

from common.views import ScopedListView

from .filters import CashDepositFilter, ExchangeRateFilter
from .models import CashDeposit, ExchangeRate
from .tables import CashDepositTable, ExchangeRateTable


class ExchangeRateListView(ScopedListView):
    model = ExchangeRate
    permission_required = "finance.view_exchangerate"
    table_class = ExchangeRateTable
    filterset_class = ExchangeRateFilter
    page_title_key = "page_exchange_rates"
    page_subtitle_key = "page_exchange_rates_sub"


class CashDepositListView(ScopedListView):
    model = CashDeposit
    permission_required = "finance.view_cashdeposit"
    table_class = CashDepositTable
    filterset_class = CashDepositFilter
    page_title_key = "page_cash_deposits"
    page_subtitle_key = "page_cash_deposits_sub"


class CashDepositReviewView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Confirm or reject a pending cash deposit (privileged action)."""

    permission_required = "finance.confirm_cashdeposit"
    raise_exception = True

    def post(self, request, pk, decision):
        deposit = get_object_or_404(CashDeposit, pk=pk)
        if decision == "confirm":
            deposit.confirm(request.user)
            log_user_action(request, "CONFIRM", instance=deposit)
            messages.success(request, _("Cash deposit confirmed."))
        elif decision == "reject":
            deposit.reject(request.user)
            log_user_action(request, "REJECT", instance=deposit)
            messages.warning(request, _("Cash deposit rejected."))
        return redirect("finance:cash_deposit_list")
