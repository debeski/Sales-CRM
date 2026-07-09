import json
import re
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory
from django.test import TestCase, override_settings
from django.urls import reverse

from catalog.models import Product, PurchaseInvoice, StockMovement, Supplier
from catalog.views import (
    OpeningStockDetailView,
    OpeningStockEditorView,
    PurchaseInvoiceCreateView,
    StockMovementListView,
)
from finance.models import ExchangeRate

User = get_user_model()
rf = RequestFactory()


def _attach_request_state(request, user):
    SessionMiddleware(lambda req: None).process_request(request)
    request.session.save()
    request.user = user
    request._messages = FallbackStorage(request)
    return request


class PurchaseInvoiceTests(TestCase):
    def setUp(self):
        ExchangeRate.objects.create(rate=Decimal("6.50"))
        self.user = User.objects.create_superuser("stockadmin", "s@example.com", "x")

    def _row(self, **over):
        base = {
            "product": "",
            "name": "",
            "unit": Product.UNIT_PIECE,
            "barcode": "",
            "cost_usd": "0.00",
            "markup_percent": "0.00",
            "price_usd": "0.00",
            "price_lyd_override": "",
            "quantity": "0.00",
        }
        base.update(over)
        return base

    def _post_data(self, rows, **header):
        data = {
            "supplier": "",
            "supplier_name": "Acme Supply",
            "supplier_phone": "0911111111",
            "supplier_address": "Tripoli",
            "invoice_date": "2026-07-09",
            "notes": "",
            "form-TOTAL_FORMS": str(len(rows)),
            "form-INITIAL_FORMS": "0",
            "form-MIN_NUM_FORMS": "0",
            "form-MAX_NUM_FORMS": "1000",
        }
        data.update(header)
        for i, row in enumerate(rows):
            for key, value in row.items():
                data[f"form-{i}-{key}"] = value
        return data

    def _post(self, data):
        req = _attach_request_state(
            rf.post(reverse("catalog:purchase_invoice_create"), data),
            self.user,
        )
        return PurchaseInvoiceCreateView.as_view()(req)

    def _get_create(self):
        req = _attach_request_state(
            rf.get(reverse("catalog:purchase_invoice_create")),
            self.user,
        )
        return PurchaseInvoiceCreateView.as_view()(req)

    def test_purchase_invoice_creates_supplier_product_line_and_stock_movement(self):
        data = self._post_data([
            self._row(
                name="Smart Lock",
                barcode="6290000000999",
                cost_usd="40.00",
                markup_percent="25.00",
                price_usd="50.00",
                quantity="5",
            )
        ])
        resp = self._post(data)

        invoice = PurchaseInvoice.objects.get()
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], reverse("catalog:purchase_invoice_detail", args=[invoice.pk]))
        self.assertEqual(invoice.number, "PINV-000001")
        self.assertEqual(invoice.total_usd, Decimal("200.00"))
        self.assertEqual(invoice.total_lyd, Decimal("1300.00"))

        supplier = Supplier.objects.get(name="Acme Supply")
        self.assertEqual((supplier.phone, supplier.address), ("0911111111", "Tripoli"))
        product = Product.objects.get(name="Smart Lock")
        self.assertEqual(product.stock_qty, Decimal("5.00"))
        self.assertEqual(product.cost_usd, Decimal("40.00"))
        self.assertEqual(product.price_usd, Decimal("50.00"))

        line = invoice.lines.get()
        self.assertEqual(line.product_id, product.pk)
        self.assertEqual(line.quantity, Decimal("5.00"))
        movement = StockMovement.objects.get(product=product)
        self.assertEqual(movement.reference, invoice.number)
        self.assertEqual(movement.purchase_invoice_id, invoice.pk)
        self.assertEqual(movement.movement_type, StockMovement.TYPE_IN)

    def test_existing_product_is_reused_and_repriced(self):
        existing = Product.objects.create(name="Existing", cost_usd=Decimal("10.00"), price_usd=Decimal("12.00"))
        Product.objects.filter(pk=existing.pk).update(stock_qty=Decimal("2.00"))

        data = self._post_data([
            self._row(product=str(existing.pk), name="Existing", cost_usd="15.00", price_usd="20.00", quantity="3")
        ])
        self._post(data)

        existing.refresh_from_db()
        self.assertEqual(Product.objects.filter(name__iexact="Existing").count(), 1)
        self.assertEqual(existing.stock_qty, Decimal("5.00"))
        self.assertEqual(existing.cost_usd, Decimal("15.00"))
        self.assertEqual(existing.price_usd, Decimal("20.00"))

    def test_attachment_widget_belongs_to_purchase_invoice_not_sales_invoice(self):
        from catalog.forms import PurchaseInvoiceForm
        from sales.forms import InvoiceForm

        pform = PurchaseInvoiceForm()
        self.assertEqual(pform.fields["attachment"].widget.template_name, "dlux/forms/file_input.html")
        self.assertTrue(pform.is_multipart())

        sform = InvoiceForm(user=None)
        self.assertNotIn("attachment", sform.fields)
        self.assertFalse(sform.is_multipart())

    def test_purchase_invoice_accepts_pdf_attachment(self):
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            data = self._post_data([
                self._row(name="With Attachment", cost_usd="10.00", price_usd="12.00", quantity="1")
            ])
            upload = SimpleUploadedFile("supplier.pdf", b"%PDF-1.4 x", content_type="application/pdf")
            resp = self._post({**data, "attachment": upload})
            invoice = PurchaseInvoice.objects.get()
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp["Location"], reverse("catalog:purchase_invoice_detail", args=[invoice.pk]))
            self.assertTrue(invoice.attachment.name.startswith("purchase_invoices/"))

    def test_product_map_includes_purchase_autofill_fields(self):
        existing = Product.objects.create(
            name="Mapped",
            unit=Product.UNIT_BOX,
            barcode="6290000000012",
            cost_usd=Decimal("42.00"),
            markup_percent=Decimal("30.00"),
            price_usd=Decimal("54.60"),
            price_lyd_override=Decimal("410.00"),
        )

        resp = self._get_create()
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        match = re.search(r'<script id="product-map" type="application/json">(.*?)</script>', html)
        self.assertIsNotNone(match)
        payload = json.loads(match.group(1))
        row = payload[str(existing.pk)]

        self.assertEqual(row["cost"], 42.0)
        self.assertEqual(row["markup"], 30.0)
        self.assertEqual(row["price_usd"], 54.6)
        self.assertEqual(row["price_lyd"], 410.0)
        self.assertEqual(row["barcode"], "6290000000012")
        self.assertEqual(row["unit"], Product.UNIT_BOX)

    def test_purchase_invoice_context_menu_prints_in_new_tab(self):
        from catalog.tables import PurchaseInvoiceTable

        invoice = PurchaseInvoice.objects.create(supplier_name="Acme")
        table = PurchaseInvoiceTable([invoice])
        actions = json.loads(table.row_attrs["data-dlux-actions"](invoice))
        print_action = next(
            action for action in actions
            if action.get("url") == reverse("catalog:purchase_invoice_print", args=[invoice.pk])
        )

        self.assertEqual(actions[0]["url"], reverse("catalog:purchase_invoice_detail", args=[invoice.pk]))
        self.assertTrue(actions[0]["dblclick"])
        self.assertEqual(print_action["target"], "_blank")


class OpeningStockOneTimeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser("openingadmin", "o@example.com", "x")
        self.product = Product.objects.create(name="Seed", cost_usd=Decimal("1.00"), price_usd=Decimal("2.00"))
        StockMovement.objects.create(
            product=self.product,
            movement_type=StockMovement.TYPE_IN,
            quantity=Decimal("1.00"),
            reason="Opening balance",
            reference="OPENING",
        )

    def test_opening_stock_editor_redirects_to_read_only_record_after_use(self):
        req = _attach_request_state(rf.get(reverse("catalog:opening_stock")), self.user)
        resp = OpeningStockEditorView.as_view()(req)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], reverse("catalog:opening_stock_detail"))

        detail_req = _attach_request_state(rf.get(reverse("catalog:opening_stock_detail")), self.user)
        detail = OpeningStockDetailView.as_view()(detail_req)
        detail.render()
        self.assertEqual(detail.status_code, 200)
        self.assertIn("Seed", detail.content.decode())
        self.assertIn("OPENING", detail.content.decode())

    def test_stock_movement_actions_switch_to_view_opening_stock(self):
        req = _attach_request_state(rf.get(reverse("catalog:stock_movement_list")), self.user)
        resp = StockMovementListView.as_view()(req)
        resp.render()
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn(reverse("catalog:opening_stock_detail"), html)
        self.assertIn(reverse("catalog:purchase_invoice_create"), html)
