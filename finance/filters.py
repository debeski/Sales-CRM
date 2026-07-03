import django_filters
from django.db.models import Q

from .models import CashDeposit, ExchangeRate


class ExchangeRateFilter(django_filters.FilterSet):
    keyword = django_filters.CharFilter(method="filter_keyword", label="")

    advanced_config = {
        "fields": [{"name": "keyword", "placeholder_key": "search_placeholder"}],
        "advanced_fields": [["source"]],
        "clear_preserve_keys": ["sort", "page"],
    }

    class Meta:
        model = ExchangeRate
        fields = ["keyword", "source"]

    def filter_keyword(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(Q(note__icontains=value) | Q(source__icontains=value))


class CashDepositFilter(django_filters.FilterSet):
    keyword = django_filters.CharFilter(method="filter_keyword", label="")

    advanced_config = {
        "fields": [
            {"name": "keyword", "placeholder_key": "search_placeholder"},
            "method",
        ],
        "advanced_fields": [["status"]],
        "clear_preserve_keys": ["sort", "page"],
    }

    class Meta:
        model = CashDeposit
        fields = ["keyword", "method", "status"]

    def filter_keyword(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(Q(reference__icontains=value) | Q(notes__icontains=value))
