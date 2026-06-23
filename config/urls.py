"""
Generated with django-lux 1.2.1.
Project name: switch-pos.
Generated on: 2026-06-22.
"""
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", include("health_check.urls")),
    path("", include("dlux.urls")),
    
    
    # DjangoLux generated routes start
    path("finance/", include(("finance.urls", "finance"), namespace="finance")),
    path("catalog/", include(("catalog.urls", "catalog"), namespace="catalog")),
    path("sales/", include(("sales.urls", "sales"), namespace="sales")),
    # DjangoLux generated routes end
]
