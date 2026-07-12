from django.urls import path

from .staff_views import (
    PublicCatalogBuilderView,
    builder_reorder,
    builder_settings,
    builder_toggle_publish,
    builder_update_listing,
)

app_name = "public_catalog_staff"

_builder = PublicCatalogBuilderView.as_view()
_builder.sidebar_group = "catalog"
_builder.sidebar_icon = "bi-shop-window"
_builder.sidebar_permissions = ["public_catalog.view_publiccataloglisting"]

# POST-only AJAX endpoints: keep them out of DLux sidebar/route discovery so they
# are never offered as navigable pages.
for _endpoint in (builder_toggle_publish, builder_update_listing, builder_reorder, builder_settings):
    _endpoint.sidebar_exclude = True

urlpatterns = [
    path("", _builder, name="builder"),
    path("toggle-publish/", builder_toggle_publish, name="builder_toggle_publish"),
    path("update-listing/", builder_update_listing, name="builder_update_listing"),
    path("reorder/", builder_reorder, name="builder_reorder"),
    path("settings/", builder_settings, name="builder_settings"),
]
