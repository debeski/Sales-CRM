from django.contrib import admin

from .models import CashDeposit, ExchangeRate


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ("rate", "source", "created_by", "created_at")
    list_filter = ("source",)
    search_fields = ("note",)


@admin.register(CashDeposit)
class CashDepositAdmin(admin.ModelAdmin):
    list_display = ("amount", "method", "status", "deposited_at", "created_by")
    list_filter = ("status", "method")
    search_fields = ("reference", "notes")
