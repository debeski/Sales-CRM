from django.urls import path

from .views import (
    CategoryListView,
    InventoryValuationView,
    ProductListView,
    ServiceListView,
    StockMovementListView,
    StockTakeApplyView,
    StockTakeCreateView,
    StockTakeDetailView,
    StockTakeListView,
)

app_name = "catalog"

# The count-create and per-take routes shouldn't appear as their own sidebar
# entries (only the Stock Takes list should).
_stock_take_create = StockTakeCreateView.as_view()
_stock_take_create.sidebar_exclude = True
_stock_take_detail = StockTakeDetailView.as_view()
_stock_take_detail.sidebar_exclude = True
_stock_take_apply = StockTakeApplyView.as_view()
_stock_take_apply.sidebar_exclude = True

urlpatterns = [
    path("", ProductListView.as_view(), name="product_list"),
    path("categories/", CategoryListView.as_view(), name="category_list"),
    path("services/", ServiceListView.as_view(), name="service_list"),
    path("stock-movements/", StockMovementListView.as_view(), name="stock_movement_list"),
    path("stock-takes/", StockTakeListView.as_view(), name="stock_take_list"),
    path("stock-takes/new/", _stock_take_create, name="stock_take_create"),
    path("stock-takes/<int:pk>/", _stock_take_detail, name="stock_take_detail"),
    path("stock-takes/<int:pk>/apply/", _stock_take_apply, name="stock_take_apply"),
    path("valuation/", InventoryValuationView.as_view(), name="inventory_valuation"),
]
