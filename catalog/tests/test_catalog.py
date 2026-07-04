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


class ProductPricingConsistencyTests(TestCase):
    """The detail view read a stored ``price_usd`` of 0 when only cost + markup
    were entered. save() now persists the derived selling price so detail views
    and downstream reads stay consistent with the (derived) list price."""

    def _make(self, **kw):
        from decimal import Decimal
        from catalog.models import Product

        defaults = dict(name="Widget", cost_usd=Decimal("100"), markup_percent=Decimal("30"))
        defaults.update(kw)
        p = Product(**defaults)
        p.save()
        return p

    def test_save_persists_derived_price_usd(self):
        from decimal import Decimal

        p = self._make()
        self.assertEqual(p.price_usd, Decimal("130.00"))

    def test_save_keeps_explicit_price_usd(self):
        from decimal import Decimal

        p = self._make(price_usd=Decimal("200.00"))
        self.assertEqual(p.price_usd, Decimal("200.00"))

    def test_modal_context_exposes_selling_price_lyd(self):
        p = self._make()
        rows = p.get_modal_context()["extra_detail_fields"]
        labels = [r["label"] for r in rows]
        self.assertTrue(any("LYD" in l or "دينار" in l for l in labels))
        # Value is the live-converted selling price, never the raw 0.
        self.assertNotIn("0.00", [r["value"] for r in rows])


class HelpTextTranslationTests(TestCase):
    def test_help_text_localized_to_arabic(self):
        from catalog.forms import ProductForm
        from common.forms import translate_help_text

        class _Req:
            session = {"lang": "ar"}

        form = ProductForm()
        translate_help_text(form, request=_Req())
        help_text = str(form.fields["price_usd"].help_text)
        # Arabic help text should not be the English literal.
        self.assertNotIn("Auto-filled", help_text)
        self.assertIn("تلقائياً", help_text)
