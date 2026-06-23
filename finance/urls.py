from django.urls import path

from .views import (
    CashDepositListView,
    CashDepositReviewView,
    ExchangeRateListView,
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
]
