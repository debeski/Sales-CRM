from django.contrib import admin

from .models import Category, Product, Service, StockMovement


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "category", "cost_usd", "price_usd", "stock_qty", "is_active")
    list_filter = ("category", "unit", "is_active", "track_stock")
    search_fields = ("name", "sku", "barcode")
    readonly_fields = ("stock_qty",)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "service_type", "price_usd", "price_lyd_override", "is_active")
    list_filter = ("service_type", "is_active")
    search_fields = ("name",)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("product", "movement_type", "quantity", "reference", "created_at")
    list_filter = ("movement_type",)
    search_fields = ("product__name", "reference")
