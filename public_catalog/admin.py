from django.contrib import admin

from .models import PublicCatalogListing, PublicContactMessage


@admin.register(PublicCatalogListing)
class PublicCatalogListingAdmin(admin.ModelAdmin):
    list_display = ("display_title", "source_kind", "slug", "is_published", "is_featured", "sort_order")
    list_filter = ("is_published", "is_featured", "show_price", "show_availability")
    search_fields = ("public_title", "public_summary", "slug", "product__name", "service__name")
    prepopulated_fields = {"slug": ("public_title",)}
    autocomplete_fields = ("product", "service")


@admin.register(PublicContactMessage)
class PublicContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "phone", "subject", "email_status", "created_at")
    list_filter = ("email_status", "created_at")
    search_fields = ("name", "email", "phone", "subject", "message", "idempotency_key")
    readonly_fields = (
        "idempotency_key",
        "name",
        "email",
        "phone",
        "subject",
        "message",
        "source_path",
        "user_agent",
        "email_status",
        "email_recipient",
        "email_sent_at",
        "email_error",
        "created_at",
        "updated_at",
    )
