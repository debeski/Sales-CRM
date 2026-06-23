from django.urls import path

from .views import (
    CategoryListView,
    ProductListView,
    ServiceListView,
    StockMovementListView,
)

app_name = "catalog"

urlpatterns = [
    path("", ProductListView.as_view(), name="product_list"),
    path("categories/", CategoryListView.as_view(), name="category_list"),
    path("services/", ServiceListView.as_view(), name="service_list"),
    path("stock-movements/", StockMovementListView.as_view(), name="stock_movement_list"),
]
