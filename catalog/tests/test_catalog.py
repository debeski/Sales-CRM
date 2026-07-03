from django.test import SimpleTestCase, TestCase

from ..urls import app_name


class CatalogConfigScaffoldTests(SimpleTestCase):
    def test_urls_namespace_matches_app_name(self):
        self.assertEqual(app_name, "catalog")


class ProductTableRenderTests(TestCase):
    def test_stock_cell_renders_for_untracked_product(self):
        # Django 6.0 format_html requires an arg; a non-stock-tracked product hits
        # the "—" branch — this raised TypeError before the fix.
        from catalog.models import Product
        from catalog.tables import ProductTable

        cell = ProductTable([]).render_stock_qty(Product(name="Gift", track_stock=False))
        self.assertIn("—", str(cell))
