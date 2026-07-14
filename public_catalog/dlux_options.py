try:
    from dlux.options import register_app_settings
except ImportError:  # pragma: no cover
    register_app_settings = None

from common.i18n import lazy_t

from .homepage import HOMEPAGE_DEFAULTS, HOMEPAGE_NS
from .settings import PUBLIC_CATALOG_DEFAULTS, PUBLIC_CATALOG_NS


if register_app_settings is not None:
    register_app_settings(
        namespace=HOMEPAGE_NS,
        title=lambda request: lazy_t("options_public_homepage", "Public homepage"),
        description=lambda request: lazy_t(
            "options_public_homepage_desc",
            "Hero copy, call-to-action and accent for the public landing page. Use the Homepage Builder for full section control.",
        ),
        icon="bi-easel2",
        order=61,
        fields=[
            {"name": "hero_kicker", "type": "char", "label": lazy_t("hp_hero_kicker", "Hero kicker"), "default": HOMEPAGE_DEFAULTS["hero_kicker"]},
            {"name": "hero_title", "type": "char", "label": lazy_t("hp_hero_title", "Hero title"), "default": ""},
            {"name": "hero_subtitle", "type": "text", "label": lazy_t("hp_hero_subtitle", "Hero subtitle"), "default": ""},
            {"name": "hero_primary_label", "type": "char", "label": lazy_t("hp_hero_primary_label", "Primary button label"), "default": HOMEPAGE_DEFAULTS["hero_primary_label"]},
            {"name": "hero_primary_url", "type": "char", "label": lazy_t("hp_hero_primary_url", "Primary button link"), "default": ""},
            {"name": "hero_show_contact", "type": "boolean", "label": lazy_t("hp_hero_show_contact", "Show Contact button"), "default": True},
            {"name": "show_stats", "type": "boolean", "label": lazy_t("hp_show_stats", "Show catalog stats"), "default": True},
            {"name": "accent", "type": "char", "label": lazy_t("hp_accent", "Accent colour (hex)"), "default": ""},
        ],
        defaults=HOMEPAGE_DEFAULTS,
    )

    register_app_settings(
        namespace=PUBLIC_CATALOG_NS,
        title=lambda request: lazy_t("options_public_catalog", "Public catalog"),
        description=lambda request: lazy_t(
            "options_public_catalog_desc",
            "Public shop title, subtitle and contact defaults.",
        ),
        icon="bi-shop",
        order=60,
        fields=[
            {"name": "homepage_enabled", "type": "boolean", "label": lazy_t("public_catalog_homepage_enabled", "Homepage live"), "default": True},
            {"name": "shop_enabled", "type": "boolean", "label": lazy_t("public_catalog_shop_enabled", "Shop live"), "default": True},
            {"name": "featured_limit", "type": "number", "label": lazy_t("public_catalog_featured_limit", "Featured items on landing"), "default": PUBLIC_CATALOG_DEFAULTS["featured_limit"], "min_value": 0, "max_value": 24},
            {"name": "shop_title", "type": "char", "label": lazy_t("public_catalog_shop_title", "Shop title"), "default": PUBLIC_CATALOG_DEFAULTS["shop_title"]},
            {"name": "shop_subtitle", "type": "text", "label": lazy_t("public_catalog_shop_subtitle", "Shop subtitle"), "default": PUBLIC_CATALOG_DEFAULTS["shop_subtitle"]},
            {"name": "contact_phone", "type": "char", "label": lazy_t("public_catalog_contact_phone", "Contact phone"), "default": ""},
            {"name": "contact_whatsapp", "type": "char", "label": lazy_t("public_catalog_contact_whatsapp", "WhatsApp number"), "default": ""},
            {"name": "contact_email", "type": "char", "label": lazy_t("public_catalog_contact_email", "Contact email"), "default": ""},
            {"name": "show_price", "type": "boolean", "label": lazy_t("public_catalog_show_price", "Show prices by default"), "default": True},
            {"name": "show_availability", "type": "boolean", "label": lazy_t("public_catalog_show_availability", "Show availability by default"), "default": True},
        ],
        defaults=PUBLIC_CATALOG_DEFAULTS,
    )
