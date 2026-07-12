from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from catalog.models import Category, Product
from public_catalog.homepage import (
    HOMEPAGE_DEFAULTS, get_homepage_config, normalize_sections, set_homepage_config,
)
from public_catalog.models import PublicCatalogListing
from public_catalog.settings import set_public_catalog_config

from .test_public_split import configure_dlux_public_split

User = get_user_model()


class HomepageConfigTests(TestCase):
    def tearDown(self):
        set_homepage_config(dict(HOMEPAGE_DEFAULTS))

    def test_normalize_sections_drops_unknown_and_appends_new(self):
        result = normalize_sections([
            {"key": "contact", "enabled": False},
            {"key": "bogus", "enabled": True},
            {"key": "featured", "enabled": True},
        ])
        keys = [s["key"] for s in result]
        # stored order first (known keys), then remaining defaults appended
        self.assertEqual(keys[:2], ["contact", "featured"])
        self.assertEqual(set(keys), {"featured", "categories", "services", "story", "contact"})
        self.assertFalse(result[0]["enabled"])  # contact stayed disabled

    def test_accent_and_overlay_are_sanitised(self):
        cfg = set_homepage_config({"accent": "0EA5E9", "hero_overlay": "250"})
        self.assertEqual(cfg["accent"], "#0ea5e9")
        self.assertEqual(cfg["hero_overlay"], 100)
        cfg = set_homepage_config({"accent": "not-a-color", "hero_overlay": "-5"})
        self.assertEqual(cfg["accent"], "")
        self.assertEqual(cfg["hero_overlay"], 0)


class HomepageBuilderViewTests(TestCase):
    def setUp(self):
        configure_dlux_public_split()
        self.admin = User.objects.create_superuser("hp_admin", "a@example.com", "x")
        self.client = Client()
        self.client.force_login(self.admin)
        cat = Category.objects.create(name="Locks")
        self.product = Product.objects.create(
            name="Deadbolt", category=cat, cost_usd=Decimal("5"), price_usd=Decimal("10"),
            track_stock=True, stock_qty=Decimal("4"),
        )
        PublicCatalogListing.objects.create(product=self.product, is_published=True, is_featured=True)

    def tearDown(self):
        set_homepage_config(dict(HOMEPAGE_DEFAULTS))
        set_public_catalog_config({"storefront_enabled": True})

    def test_builder_page_renders(self):
        resp = self.client.get(reverse("public_catalog_staff:homepage_builder"))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("data-hpb-frame", html)
        self.assertIn("data-hpb-sections", html)
        self.assertIn("preview=1", html)

    def test_save_persists_hero_accent_and_section_order(self):
        resp = self.client.post(reverse("public_catalog_staff:homepage_save"), {
            "hero_title": "Secure your space",
            "hero_media": "gradient",
            "hero_overlay": "70",
            "accent": "#0ea5e9",
            "featured_heading": "Our picks",
            "sections": '[{"key":"story","enabled":true},{"key":"featured","enabled":true}]',
        })
        self.assertEqual(resp.status_code, 200)
        cfg = get_homepage_config()
        self.assertEqual(cfg["hero_title"], "Secure your space")
        self.assertEqual(cfg["hero_media"], "gradient")
        self.assertEqual(cfg["hero_overlay"], 70)
        self.assertEqual(cfg["accent"], "#0ea5e9")
        self.assertEqual([s["key"] for s in cfg["sections"]][:2], ["story", "featured"])

    def test_landing_reflects_config(self):
        set_homepage_config({
            "hero_title": "Secure your space", "hero_media": "gradient",
            "accent": "#0ea5e9", "story_heading": "Who we are",
            "sections": [{"key": "story", "enabled": True}, {"key": "featured", "enabled": True}],
        })
        html = self.client.get(reverse("public_catalog:landing")).content.decode()
        self.assertIn("Secure your space", html)
        self.assertIn("--public-accent:#0ea5e9", html)
        self.assertIn("public-hero--gradient", html)
        self.assertIn("Who we are", html)

    def test_staff_preview_bypasses_offline_gate(self):
        set_public_catalog_config({"storefront_enabled": False})
        anon = Client()
        self.assertEqual(anon.get(reverse("public_catalog:landing")).status_code, 503)
        self.assertEqual(anon.get(reverse("public_catalog:landing") + "?preview=1").status_code, 503)
        # authed staff with permission may preview the offline storefront
        self.assertEqual(self.client.get(reverse("public_catalog:landing") + "?preview=1").status_code, 200)

    def test_get_on_save_is_silent_no_op(self):
        resp = self.client.get(reverse("public_catalog_staff:homepage_save"))
        self.assertEqual(resp.status_code, 204)

    def test_save_requires_change_permission(self):
        plain = User.objects.create_user("hp_plain", password="x")
        client = Client()
        client.force_login(plain)
        resp = client.post(reverse("public_catalog_staff:homepage_save"), {"hero_title": "x"})
        self.assertEqual(resp.status_code, 403)
