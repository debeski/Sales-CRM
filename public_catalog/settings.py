from urllib.parse import quote

from dlux.options import write_app_system_config
from dlux.utils import get_app_system_config

PUBLIC_CATALOG_NS = "switch_pos.public_catalog"

PUBLIC_CATALOG_DEFAULTS = {
    "shop_title": "Switch Shop",
    "shop_subtitle": "Smart locks, access control, installation and after-sale services.",
    "contact_phone": "",
    "contact_whatsapp": "",
    "contact_email": "",
    "show_price": True,
    "show_availability": True,
    "storefront_enabled": True,
    "featured_limit": 4,
}


def get_public_catalog_config():
    stored = get_app_system_config(PUBLIC_CATALOG_NS, {}) or {}
    if not isinstance(stored, dict):
        stored = {}
    cfg = {**PUBLIC_CATALOG_DEFAULTS, **stored}
    cfg["show_price"] = bool(cfg.get("show_price"))
    cfg["show_availability"] = bool(cfg.get("show_availability"))
    cfg["storefront_enabled"] = bool(cfg.get("storefront_enabled"))
    try:
        cfg["featured_limit"] = max(0, int(cfg.get("featured_limit") or 0))
    except (TypeError, ValueError):
        cfg["featured_limit"] = PUBLIC_CATALOG_DEFAULTS["featured_limit"]
    return cfg


def set_public_catalog_config(patch, *, request=None):
    cfg = get_public_catalog_config()
    cfg.update({k: v for k, v in patch.items() if k in PUBLIC_CATALOG_DEFAULTS})
    write_app_system_config(PUBLIC_CATALOG_NS, cfg, request=request)
    return cfg


def contact_links(listing=None):
    cfg = get_public_catalog_config()
    title = listing.display_title if listing is not None else cfg["shop_title"]
    message = quote(f"Hello, I am interested in {title}.")
    links = []
    phone = str(cfg.get("contact_phone") or "").strip()
    whatsapp = str(cfg.get("contact_whatsapp") or "").strip()
    email = str(cfg.get("contact_email") or "").strip()
    if whatsapp:
        normalized = "".join(ch for ch in whatsapp if ch.isdigit())
        if normalized:
            links.append({
                "label": "WhatsApp",
                "icon": "bi-whatsapp",
                "url": f"https://wa.me/{normalized}?text={message}",
                "kind": "whatsapp",
            })
    if phone:
        links.append({
            "label": "Call",
            "icon": "bi-telephone",
            "url": f"tel:{phone}",
            "kind": "phone",
        })
    if email:
        links.append({
            "label": "Email",
            "icon": "bi-envelope",
            "url": f"mailto:{email}?subject={quote(title)}",
            "kind": "email",
        })
    return links

