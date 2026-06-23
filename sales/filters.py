import django_filters
from django.db.models import Q

from .models import Customer, Invoice, Payment


class InvoiceFilter(django_filters.FilterSet):
    keyword = django_filters.CharFilter(method="filter_keyword", label="")
    date_from = django_filters.DateFilter(field_name="invoice_date", lookup_expr="gte", label="From")
    date_to = django_filters.DateFilter(field_name="invoice_date", lookup_expr="lte", label="To")

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

    class Meta:
        model = Customer
        fields = ["keyword", "is_active"]

    def filter_keyword(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(Q(name__icontains=value) | Q(phone__icontains=value))


class PaymentFilter(django_filters.FilterSet):
    keyword = django_filters.CharFilter(method="filter_keyword", label="")

    class Meta:
        model = Payment
        fields = ["keyword", "method"]

    def filter_keyword(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(Q(invoice__number__icontains=value) | Q(notes__icontains=value))
