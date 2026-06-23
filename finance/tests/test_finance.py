from django.test import SimpleTestCase

from ..urls import app_name


class FinanceConfigScaffoldTests(SimpleTestCase):
    def test_urls_namespace_matches_app_name(self):
        self.assertEqual(app_name, "finance")
