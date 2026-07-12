import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from catalog.models import Product, Service
from public_catalog.models import PublicCatalogListing
from public_catalog.settings import get_public_catalog_config, set_public_catalog_config

from .test_public_split import configure_dlux_public_split

User = get_user_model()


class PublicCatalogBuilderTests(TestCase):
    def setUp(self):
        configure_dlux_public_split()
        self.admin = User.objects.create_superuser("builder_admin", "a@example.com", "x")
        self.client = Client()
        self.client.force_login(self.admin)
        self.product = Product.objects.create(
            name="Smart Lock", cost_usd=Decimal("10"), price_usd=Decimal("20"),
            track_stock=True, stock_qty=Decimal("8"),
        )
        self.service = Service.objects.create(name="Installation", service_type="installation")

    def test_builder_page_lists_stock_items(self):
        resp = self.client.get(reverse("public_catalog_staff:builder"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("Smart Lock", html)
        self.assertIn("Installation", html)
        self.assertIn("data-toggle-url", html)
        self.assertIn('data-kind="product"', html)
        self.assertIn('data-kind="service"', html)

    def test_toggle_publish_creates_then_flips(self):
        url = reverse("public_catalog_staff:builder_toggle_publish")
        resp = self.client.post(url, {"kind": "product", "id": self.product.pk})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()["listing"]
        self.assertTrue(data["is_published"])
        listing = PublicCatalogListing.objects.get(product=self.product)
        self.assertTrue(listing.is_published)

        resp2 = self.client.post(url, {"listing_id": listing.pk})
        self.assertFalse(resp2.json()["listing"]["is_published"])
        listing.refresh_from_db()
        self.assertFalse(listing.is_published)

    def test_update_listing_sets_overrides(self):
        url = reverse("public_catalog_staff:builder_update_listing")
        resp = self.client.post(url, {
            "kind": "product", "id": self.product.pk,
            "public_title": "Premium Smart Lock",
            "public_summary": "Keyless entry",
            "show_price": "0",
        })
        self.assertEqual(resp.status_code, 200)
        listing = PublicCatalogListing.objects.get(product=self.product)
        self.assertEqual(listing.public_title, "Premium Smart Lock")
        self.assertEqual(listing.public_summary, "Keyless entry")
        self.assertFalse(listing.show_price)

    def test_feature_only_applies_when_published(self):
        url = reverse("public_catalog_staff:builder_update_listing")
        # Not published yet -> featuring is refused (cleared on save).
        self.client.post(url, {"kind": "product", "id": self.product.pk, "is_featured": "1"})
        listing = PublicCatalogListing.objects.get(product=self.product)
        self.assertFalse(listing.is_featured)
        # Publish then feature.
        self.client.post(reverse("public_catalog_staff:builder_toggle_publish"),
                         {"listing_id": listing.pk})
        self.client.post(url, {"listing_id": listing.pk, "is_featured": "1"})
        listing.refresh_from_db()
        self.assertTrue(listing.is_featured)

    def test_reorder_sets_sort_order(self):
        a = PublicCatalogListing.objects.create(product=self.product, is_published=True, sort_order=5)
        b = PublicCatalogListing.objects.create(service=self.service, is_published=True, sort_order=5)
        resp = self.client.post(
            reverse("public_catalog_staff:builder_reorder"),
            data=json.dumps([b.pk, a.pk]),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        b.refresh_from_db(); a.refresh_from_db()
        self.assertEqual(b.sort_order, 0)
        self.assertEqual(a.sort_order, 1)

    def test_settings_toggle_persists_and_gates_public(self):
        resp = self.client.post(
            reverse("public_catalog_staff:builder_settings"),
            {"storefront_enabled": "0", "featured_limit": "6"},
        )
        self.assertEqual(resp.status_code, 200)
        cfg = get_public_catalog_config()
        self.assertFalse(cfg["storefront_enabled"])
        self.assertEqual(cfg["featured_limit"], 6)
        # Public storefront now shows the coming-soon page.
        anon = Client()
        landing = anon.get(reverse("public_catalog:landing"))
        self.assertEqual(landing.status_code, 503)
        self.assertIn("public-comingsoon", landing.content.decode())

    def test_get_on_write_endpoints_is_silent_no_op(self):
        # Browser speculative prefetch (GET) must not 405 or mutate — it returns 204.
        for name in ("builder_toggle_publish", "builder_update_listing",
                     "builder_reorder", "builder_settings"):
            resp = self.client.get(reverse("public_catalog_staff:" + name))
            self.assertEqual(resp.status_code, 204)
        self.assertFalse(PublicCatalogListing.objects.filter(product=self.product).exists())

    def test_sidebar_discovery_only_exposes_builder_page(self):
        from dlux.discovery import _discover_sidebar_catalog_uncached

        en_catalog = _discover_sidebar_catalog_uncached(lang_code="en", include_system_items=True, config={})
        ar_catalog = _discover_sidebar_catalog_uncached(lang_code="ar", include_system_items=True, config={})

        names = {
            entry["url_name"]
            for entry in en_catalog
            if entry["url_name"].startswith("public_catalog_staff:")
        }
        en_entry = next(entry for entry in en_catalog if entry["url_name"] == "public_catalog_staff:builder")
        ar_entry = next(entry for entry in ar_catalog if entry["url_name"] == "public_catalog_staff:builder")

        self.assertEqual(names, {"public_catalog_staff:builder"})
        self.assertEqual(en_entry["label"], "Public Catalog Builder")
        self.assertEqual(ar_entry["label"], "منشئ المتجر العام")

    def test_browser_navigation_to_write_endpoint_redirects_to_builder(self):
        resp = self.client.get(
            reverse("public_catalog_staff:builder_settings"),
            HTTP_SEC_FETCH_MODE="navigate",
            HTTP_ACCEPT="text/html",
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp["Location"], reverse("public_catalog_staff:builder"))
        self.assertFalse(PublicCatalogListing.objects.filter(product=self.product).exists())

    def test_edit_endpoints_require_change_permission(self):
        plain = User.objects.create_user("plain_shop", password="x")
        client = Client()
        client.force_login(plain)
        resp = client.post(reverse("public_catalog_staff:builder_toggle_publish"),
                           {"kind": "product", "id": self.product.pk})
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(PublicCatalogListing.objects.filter(product=self.product).exists())

    def tearDown(self):
        set_public_catalog_config({"storefront_enabled": True})
