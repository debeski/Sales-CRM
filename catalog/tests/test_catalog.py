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


class ProductVariantFieldTests(TestCase):
    def test_color_palette_has_15_common_unique_choices(self):
        from catalog.models import Product

        values = [value for value, _label in Product.COLOR_CHOICES]
        self.assertEqual(len(values), 15)
        self.assertEqual(len(values), len(set(values)))
        self.assertEqual(values.count(Product.COLOR_BLACK), 1)
        self.assertEqual(values.count(Product.COLOR_GRAY), 1)
        self.assertEqual(values.count(Product.COLOR_WHITE), 1)

    def test_product_form_keeps_variants_out_of_manual_product_create(self):
        from catalog.forms import ProductForm

        form = ProductForm()
        self.assertNotIn("color", form.fields)
        self.assertNotIn("size", form.fields)

    def test_product_detail_and_table_render_available_variant_quantities(self):
        from decimal import Decimal

        from catalog.models import Product, ProductVariant
        from catalog.tables import ProductTable

        product = Product.objects.create(name="Spare Key")
        ProductVariant.objects.create(product=product, color=Product.COLOR_ORANGE, size="13.56 MHz", stock_qty=Decimal("2.00"))
        ProductVariant.objects.create(product=product, color=Product.COLOR_BLUE, size="13.56 MHz", stock_qty=Decimal("3.00"))

        detail_html = str(product.get_modal_context()["extra_detail_fields"][-1]["value"])
        table_html = str(ProductTable([]).render_color(product))
        self.assertIn("Orange", detail_html)
        self.assertIn("Blue", detail_html)
        self.assertIn("× 2", detail_html)
        self.assertIn("× 3", table_html)


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


class CatalogTranslationParityTests(TestCase):
    def test_english_and_arabic_keys_match(self):
        from catalog.translations import DLUX_STRINGS

        self.assertEqual(set(DLUX_STRINGS["en"]), set(DLUX_STRINGS["ar"]))
