from common.views import ScopedListView

from .filters import CategoryFilter, ProductFilter, ServiceFilter, StockMovementFilter
from .models import Category, Product, Service, StockMovement
from .tables import CategoryTable, ProductTable, ServiceTable, StockMovementTable


class CategoryListView(ScopedListView):
    model = Category
    permission_required = "catalog.view_category"
    table_class = CategoryTable
    filterset_class = CategoryFilter
    page_title_key = "page_categories"


class ProductListView(ScopedListView):
    model = Product
    permission_required = "catalog.view_product"
    table_class = ProductTable
    filterset_class = ProductFilter
    page_title_key = "page_products"
    page_subtitle_key = "page_products_sub"


class ServiceListView(ScopedListView):
    model = Service
    permission_required = "catalog.view_service"
    table_class = ServiceTable
    filterset_class = ServiceFilter
    page_title_key = "page_services"
    page_subtitle_key = "page_services_sub"


class StockMovementListView(ScopedListView):
    model = StockMovement
    permission_required = "catalog.view_stockmovement"
    table_class = StockMovementTable
    filterset_class = StockMovementFilter
    page_title_key = "page_stock_movements"
    page_subtitle_key = "page_stock_movements_sub"
