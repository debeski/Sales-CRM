from django.urls import path

from .views import (
    CashDepositListView,
    CashDepositReviewView,
    ExchangeRateListView,
    ExpenseCategoryListView,
    ExpenseListView,
    ExpenseReviewView,
    StaffAccountDetailView,
    StaffAccountListView,
    StaffLedgerEntryActionView,
    StaffLedgerEntryListView,
)

app_name = "finance"

urlpatterns = [
    path("rates/", ExchangeRateListView.as_view(), name="exchange_rate_list"),
    path("deposits/", CashDepositListView.as_view(), name="cash_deposit_list"),
    path(
        "deposits/<int:pk>/<str:decision>/",
        CashDepositReviewView.as_view(),
        name="cash_deposit_review",
    ),
    path("expense-categories/", ExpenseCategoryListView.as_view(), name="expense_category_list"),
    path("expenses/", ExpenseListView.as_view(), name="expense_list"),
    path("expenses/<int:pk>/<str:decision>/", ExpenseReviewView.as_view(), name="expense_review"),
    path("staff-accounts/", StaffAccountListView.as_view(), name="staff_account_list"),
    path("staff-accounts/<int:pk>/", StaffAccountDetailView.as_view(), name="staff_account_detail"),
    path("staff-ledger/", StaffLedgerEntryListView.as_view(), name="staff_ledger_entry_list"),
    path("staff-ledger/<int:pk>/<str:action>/", StaffLedgerEntryActionView.as_view(), name="staff_ledger_entry_action"),
]
