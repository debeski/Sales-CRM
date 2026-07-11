"""DjangoLux Options-page registrations for the Products layout.

Auto-imported at startup by dlux's option autodiscovery (`<app>.dlux_options`).

Two surfaces:
  * A per-user picker **card** (`register_card`) — every user who can view
    products chooses their own layout; persisted to their profile preferences.
  * A superuser **settings tile** (`register_app_settings`, dlux >= 1.4.4) that
    sets the shop-wide *default* layout, saved to
    `SystemSettings.extra_config['app']['switch_pos.products_layout']`. The
    per-user pick overrides it; otherwise everyone gets this default.
"""
from dlux.options import register_card

from common.i18n import t

from .product_layouts import (
    PRODUCTS_LAYOUT_DEFAULT_FIELD, PRODUCTS_LAYOUT_NS, get_products_layout,
)

# register_app_settings (global admin defaults in extra_config) is dlux >= 1.4.4.
# Import defensively so an older runtime still gets the per-user card above.
try:
    from dlux.options import register_app_settings
except ImportError:  # pragma: no cover - depends on runtime dlux version
    register_app_settings = None


def _title(request):
    return t("options_products_layout", "Products layout")


def _context(request):
    return {
        "products_layout": get_products_layout(request),
        "products_layout_ns": PRODUCTS_LAYOUT_NS,
    }


register_card(
    id="switch_pos.products_layout",
    title=_title,
    template_name="catalog/options/products_layout_card.html",
    icon="bi-grid-3x3-gap",
    order=50,
    permission="catalog.view_product",
    context_builder=_context,
)


if register_app_settings is not None:
    register_app_settings(
        namespace=PRODUCTS_LAYOUT_NS,
        title=lambda request: t("options_products_layout_default", "Default products layout"),
        description=lambda request: t(
            "options_products_layout_default_desc",
            "The shop-wide default Products view. Each user can still override it for themselves.",
        ),
        icon="bi-grid-3x3-gap",
        order=50,
        fields=[
            {
                "name": PRODUCTS_LAYOUT_DEFAULT_FIELD,
                "type": "choice",
                "control": "selector",
                "label": t("options_products_layout_default", "Default products layout"),
                "choices": [
                    ("table", t("products_layout_table", "Table")),
                    ("grid", t("products_layout_grid", "Grid")),
                    ("light", t("products_layout_light", "Light")),
                ],
                "default": "table",
            },
        ],
        defaults={PRODUCTS_LAYOUT_DEFAULT_FIELD: "table"},
    )
