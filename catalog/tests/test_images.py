"""
Product/Service image field — upload, list thumbnail, and detail rendering.
"""
import tempfile
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from catalog.forms import ProductForm, ServiceForm
from catalog.models import Product, Service
from catalog.tables import ProductTable, ServiceTable

MEDIA = tempfile.mkdtemp(prefix="switchpos-test-media-")


def _png_upload(name="p.png"):
    """A tiny valid PNG so ImageField's Pillow validation passes."""
    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (2, 2), (200, 40, 40)).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=MEDIA)
class ProductImageTests(TestCase):
    def test_form_accepts_image_upload(self):
        form = ProductForm(
            data={
                "name": "Smart Lock", "unit": "piece", "cost_usd": "10",
                "markup_percent": "0", "price_usd": "10", "reorder_level": "0",
            },
            files={"image": _png_upload()},
        )
        self.assertTrue(form.is_valid(), form.errors)
        product = form.save()
        self.assertTrue(product.image.name.startswith("catalog/products/"))

    def test_form_uses_dlux_archive_widget_with_accept(self):
        form = ProductForm()
        self.assertIn("image", form.fields)
        widget = form.fields["image"].widget
        # dlux's rich archive file field (drag-drop card), not the plain input.
        self.assertEqual(widget.template_name, "dlux/forms/file_input.html")
        self.assertEqual(widget.attrs.get("accept"), "image/*")  # phone camera preserved
        self.assertFalse(form.fields["image"].required)
        self.assertIn("data-archive-file-widget", str(form["image"]))  # renders the card

    def test_table_thumbnail_and_placeholder(self):
        with_img = Product.objects.create(name="A", cost_usd=Decimal("1"), image=_png_upload("a.png"))
        without = Product.objects.create(name="B", cost_usd=Decimal("1"))
        table = ProductTable([])
        self.assertIn("<img", table.render_image(with_img))
        self.assertNotIn("<img", table.render_image(without))  # placeholder icon

    def test_detail_context_includes_image_row(self):
        p = Product.objects.create(name="A", cost_usd=Decimal("1"), image=_png_upload("d.png"))
        rows = p.get_modal_context()["extra_detail_fields"]
        self.assertTrue(any(r.get("is_html") and "<img" in r["value"] for r in rows))
        # No image -> no image row.
        plain = Product.objects.create(name="C", cost_usd=Decimal("1"))
        self.assertFalse(any(r.get("is_html") for r in plain.get_modal_context()["extra_detail_fields"]))


class GridLayoutTests(TestCase):
    """Modal forms get a multi-column crispy layout (common.forms.build_grid_helper)
    so short fields share a row — the dlux modal renders {% crispy form %} but
    attaches no layout, so without this each field stacks full-width."""

    def test_product_form_has_multicolumn_layout(self):
        from crispy_forms.utils import render_crispy_form

        form = ProductForm()
        self.assertTrue(getattr(form, "helper", None) and form.helper.layout)
        html = render_crispy_form(form)
        self.assertIn('class="row', html)          # at least one grid row
        self.assertIn("col-md-6", html)            # paired fields
        self.assertIn("col-md-4", html)            # the 3-across price row
        # No field is silently dropped by the custom layout.
        for name in form.fields:
            self.assertIn(f'name="{name}"', html, f"field {name} missing from layout")

    def test_track_stock_has_help_text(self):
        # track_stock now carries an explanatory description (help_product_track_stock).
        self.assertTrue(ProductForm().fields["track_stock"].help_text)

    def test_grid_helper_drops_absent_fields(self):
        # A field name not on the form is ignored (no crash), present ones render.
        from django import forms as djforms

        from common.forms import build_grid_helper

        class F(djforms.Form):
            a = djforms.CharField()
            b = djforms.CharField()

        f = F()
        build_grid_helper(f, [("a", "does_not_exist"), ("b",)])
        self.assertTrue(f.helper.layout)


@override_settings(MEDIA_ROOT=MEDIA)
class ServiceImageTests(TestCase):
    def test_service_form_and_thumbnail(self):
        form = ServiceForm(
            data={"name": "Install", "service_type": "installation", "price_usd": "5"},
            files={"image": _png_upload("s.png")},
        )
        self.assertTrue(form.is_valid(), form.errors)
        svc = form.save()
        self.assertTrue(svc.image.name.startswith("catalog/services/"))
        self.assertIn("<img", ServiceTable([]).render_image(svc))
        self.assertIn("<img", Service.objects.get(pk=svc.pk).get_modal_context()["extra_detail_fields"][0]["value"])
