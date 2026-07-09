import django_filters
from django.db.models import Q

from .models import Customer, Delivery, Invoice, Payment


class InvoiceFilter(django_filters.FilterSet):
    keyword = django_filters.CharFilter(method="filter_keyword", label="")
    date_from = django_filters.DateFilter(field_name="invoice_date", lookup_expr="gte", label="From")
    date_to = django_filters.DateFilter(field_name="invoice_date", lookup_expr="lte", label="To")

    # advanced_filter_helper layout: keyword + status in the primary row, the
    # date range inside the advanced collapse.
    advanced_config = {
        "fields": [
            {"name": "keyword", "placeholder_key": "search_placeholder"},
            "status",
        ],
        "advanced_fields": [
            [
                {"name": "date_from", "range_label_key": "label_invoice_date", "range_direction": "from"},
                {"name": "date_to", "range_label_key": "label_invoice_date", "range_direction": "to"},
            ],
        ],
        "clear_preserve_keys": ["sort", "page"],
    }

    class Meta:
        model = Invoice
        fields = ["keyword", "status", "date_from", "date_to"]

    def filter_keyword(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(number__icontains=value)
            | Q(customer_name__icontains=value)
            | Q(customer__name__icontains=value)
            | Q(customer_phone__icontains=value)
        )


class CustomerFilter(django_filters.FilterSet):
    keyword = django_filters.CharFilter(method="filter_keyword", label="")

    advanced_config = {
        "fields": [{"name": "keyword", "placeholder_key": "search_placeholder"}],
        "advanced_fields": [["is_active"]],
        "clear_preserve_keys": ["sort", "page"],
    }

    class Meta:
        model = Customer
        fields = ["keyword", "is_active"]

    def filter_keyword(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(phone__icontains=value))


class PaymentFilter(django_filters.FilterSet):
    keyword = django_filters.CharFilter(method="filter_keyword", label="")

    advanced_config = {
        "fields": [{"name": "keyword", "placeholder_key": "search_placeholder"}],
        "advanced_fields": [["method"]],
        "clear_preserve_keys": ["sort", "page"],
    }

    class Meta:
        model = Payment
        fields = ["keyword", "method"]

    def filter_keyword(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(receipt_number__icontains=value)
            | Q(invoice__number__icontains=value)
            | Q(notes__icontains=value)
        )


class DeliveryFilter(django_filters.FilterSet):
    keyword = django_filters.CharFilter(method="filter_keyword", label="")

    advanced_config = {
        "fields": [
            {"name": "keyword", "placeholder_key": "search_placeholder"},
            "status",
        ],
        "advanced_fields": [["scheduled_date"]],
        "clear_preserve_keys": ["sort", "page"],
    }

    class Meta:
        model = Delivery
        fields = ["keyword", "status", "scheduled_date"]

    def filter_keyword(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(recipient__icontains=value)
            | Q(address__icontains=value)
            | Q(phone__icontains=value)
            | Q(invoice__number__icontains=value)
        )
