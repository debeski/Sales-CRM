from django.test import SimpleTestCase

from ..urls import app_name


class CatalogConfigScaffoldTests(SimpleTestCase):
    def test_urls_namespace_matches_app_name(self):
        self.assertEqual(app_name, "catalog")
