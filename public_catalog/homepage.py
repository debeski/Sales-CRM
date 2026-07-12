"""Public homepage (landing page) configuration.

Stored in the DLux app-settings store under its own namespace, exactly like the
public catalog / products-layout settings. The homepage builder writes here; the
public landing view reads a resolved config + an ordered list of enabled sections.
"""
from dlux.options import write_app_system_config
from dlux.utils import get_app_system_config

HOMEPAGE_NS = "switch_pos.public_homepage"

# Order matters: this is the default section order on a fresh install.
SECTION_KEYS = ("featured", "categories", "services", "story", "contact")

DEFAULT_SECTIONS = [
    {"key": "featured", "enabled": True},
    {"key": "categories", "enabled": False},
    {"key": "services", "enabled": False},
    {"key": "story", "enabled": False},
    {"key": "contact", "enabled": True},
]

HERO_MEDIA_MODES = ("featured", "logo", "custom", "gradient")

HOMEPAGE_DEFAULTS = {
    # Hero
    "hero_kicker": "Switch Libya",
    "hero_title": "",            # blank -> shop_title
    "hero_subtitle": "",         # blank -> shop_subtitle
    "hero_primary_label": "Shop",
    "hero_primary_url": "",      # blank -> public shop
    "hero_show_contact": True,
    "hero_media": "featured",    # featured | logo | custom | gradient
    "hero_image": "",            # media url when hero_media == custom
    "hero_overlay": 55,          # 0-100 scrim strength
    "show_stats": True,
    # Site accent (blank -> theme default)
    "accent": "",
    # Per-section copy
    "featured_kicker": "Featured catalog",
    "featured_heading": "Ready for customer viewing",
    "categories_kicker": "Categories",
    "categories_heading": "Browse by category",
    "services_kicker": "What we do",
    "services_heading": "Services we provide",
    "story_kicker": "Who we are",
    "story_heading": "About Switch",
    "story_body": "",
    "story_image": "",
    "contact_kicker": "Contact",
    "contact_heading": "Talk to Switch about supply and installation",
    # Ordered, toggleable sections
    "sections": DEFAULT_SECTIONS,
}

_BOOL_KEYS = ("hero_show_contact", "show_stats")
_TEXT_KEYS = tuple(
    k for k, v in HOMEPAGE_DEFAULTS.items()
    if isinstance(v, str)
)


def _clamp_overlay(value):
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return HOMEPAGE_DEFAULTS["hero_overlay"]


def normalize_sections(stored):
    """Return a clean [{key, enabled}] list: stored order first (deduped, known
    keys only), then any newly-added default sections appended."""
    result, seen = [], set()
    if isinstance(stored, list):
        for item in stored:
            key = item.get("key") if isinstance(item, dict) else None
            if key in SECTION_KEYS and key not in seen:
                result.append({"key": key, "enabled": bool(item.get("enabled", True))})
                seen.add(key)
    for default in DEFAULT_SECTIONS:
        if default["key"] not in seen:
            result.append(dict(default))
            seen.add(default["key"])
    return result


def get_homepage_config():
    stored = get_app_system_config(HOMEPAGE_NS, {}) or {}
    if not isinstance(stored, dict):
        stored = {}
    cfg = {**HOMEPAGE_DEFAULTS, **stored}
    for key in _BOOL_KEYS:
        cfg[key] = bool(cfg.get(key))
    cfg["hero_overlay"] = _clamp_overlay(cfg.get("hero_overlay"))
    if cfg.get("hero_media") not in HERO_MEDIA_MODES:
        cfg["hero_media"] = HOMEPAGE_DEFAULTS["hero_media"]
    cfg["accent"] = _sanitize_hex(cfg.get("accent"))
    cfg["sections"] = normalize_sections(cfg.get("sections"))
    return cfg


def _sanitize_hex(value):
    value = str(value or "").strip()
    if not value:
        return ""
    if not value.startswith("#"):
        value = "#" + value
    body = value[1:]
    if len(body) in (3, 6) and all(c in "0123456789abcdefABCDEF" for c in body):
        return value.lower()
    return ""


def set_homepage_config(patch, *, request=None):
    cfg = get_homepage_config()
    for key, value in patch.items():
        if key not in HOMEPAGE_DEFAULTS:
            continue
        if key == "sections":
            cfg[key] = normalize_sections(value)
        elif key in _BOOL_KEYS:
            cfg[key] = bool(value)
        elif key == "hero_overlay":
            cfg[key] = _clamp_overlay(value)
        elif key == "accent":
            cfg[key] = _sanitize_hex(value)
        else:
            cfg[key] = value
    write_app_system_config(HOMEPAGE_NS, cfg, request=request)
    return cfg


def resolve_sections(cfg=None):
    """Ordered sections with their resolved copy, for template iteration."""
    from common.i18n import t

    cfg = cfg or get_homepage_config()
    resolved = []
    for section in cfg["sections"]:
        key = section["key"]
        resolved.append({
            "key": key,
            "label": t(f"hp_section_{key}", key.capitalize()),
            "enabled": bool(section.get("enabled")),
            "kicker": cfg.get(f"{key}_kicker", ""),
            "heading": cfg.get(f"{key}_heading", ""),
        })
    return resolved
