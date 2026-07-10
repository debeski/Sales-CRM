from django.contrib import admin

from .models import (
    CashDeposit, ExchangeRate, Expense, ExpenseCategory, StaffAccount, StaffLedgerEntry,
)


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


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("category", "amount_lyd", "expense_date", "method", "status", "paid_by")
    list_filter = ("status", "method", "category")
    search_fields = ("reference", "notes", "category__name")


@admin.register(StaffAccount)
class StaffAccountAdmin(admin.ModelAdmin):
    list_display = ("user", "is_active")
    search_fields = ("user__username", "user__first_name", "user__last_name")


@admin.register(StaffLedgerEntry)
class StaffLedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("account", "entry_type", "amount_lyd", "signed_amount", "entry_date", "status")
    list_filter = ("status", "entry_type")
    search_fields = ("reference", "notes", "account__user__username")
