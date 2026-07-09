from django.contrib import admin

from .models import Customer, Invoice, InvoiceItem, Payment


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ("receipt_number",)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "is_active")
    search_fields = ("name", "phone")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "display_customer", "status", "invoice_date", "total_lyd", "amount_paid")
    list_filter = ("status", "invoice_date")
    search_fields = ("number", "customer_name", "customer__name")
    readonly_fields = ("number", "subtotal_lyd", "total_lyd", "amount_paid", "exchange_rate_obj", "issued_at")
    inlines = [InvoiceItemInline, PaymentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("receipt_number", "invoice", "amount", "method", "paid_at", "created_by")
    list_filter = ("method",)
    search_fields = ("receipt_number", "invoice__number")
    readonly_fields = ("receipt_number",)
