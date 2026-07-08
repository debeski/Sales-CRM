"""
Generated with django-lux 1.2.1.
Project name: switch-pos.
Generated on: 2026-06-22.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from dlux.views import DynamicModalDeleteView, DynamicModalManagerView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", include("health_check.urls")),
    # Project-scoped dynamic-modal routes: form-only (no embedded records table),
    # so add/edit modals show just the form. Row edit/view/delete on list pages
    # are wired to these by common/static/common/js/scoped_crud.js.
    path(
        "app-modals/<str:app_label>/<str:model_name>/<str:pk>/delete/",
        DynamicModalDeleteView.as_view(),
        name="scoped_modal_delete",
    ),
    path(
        "app-modals/<str:app_label>/<str:model_name>/<str:pk>/",
        DynamicModalManagerView.as_view(show_table=False),
        name="scoped_modal_manager",
    ),
    path("", include("dlux.urls")),


    # DjangoLux generated routes start
    path("finance/", include(("finance.urls", "finance"), namespace="finance")),
    path("catalog/", include(("catalog.urls", "catalog"), namespace="catalog")),
    path("sales/", include(("sales.urls", "sales"), namespace="sales")),
    # DjangoLux generated routes end
]

# Serve uploaded media via Django only in DEBUG (local runserver). In production
# Caddy file_servers /media/ directly; static() returns [] when DEBUG is False.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
