"""
Currency conversion helpers — the single source of truth for USD <-> LYD math.

Reuse these everywhere instead of multiplying by a rate inline; it keeps rounding
consistent and means there is exactly one place that decides what "the current
rate" is.
"""
from decimal import Decimal, ROUND_HALF_UP

from django.core.cache import cache

from .models import CURRENT_RATE_CACHE_KEY, ExchangeRate

# Sensible fallback so the system is usable before an admin sets the first rate.
# Surfaced in the UI as "no rate set" — never silently relied upon for real sales.
DEFAULT_RATE = Decimal("6.00")

LYD_QUANT = Decimal("0.01")
USD_QUANT = Decimal("0.01")


def get_current_rate():
    """Return the live USD->LYD rate as a Decimal (newest ExchangeRate row).

    Cached to keep product-list price computations from issuing one query per row.
    Returns ``DEFAULT_RATE`` if no rate has ever been configured.
    """
    cached = cache.get(CURRENT_RATE_CACHE_KEY)
    if cached is not None:
        return Decimal(cached)
    latest = ExchangeRate.objects.order_by("-created_at").values_list("rate", flat=True).first()
    rate = Decimal(latest) if latest is not None else DEFAULT_RATE
    cache.set(CURRENT_RATE_CACHE_KEY, rate, 60 * 60)
    return rate


def has_configured_rate():
    """True once an admin has entered at least one real exchange rate."""
    if cache.get(CURRENT_RATE_CACHE_KEY) is not None:
        return True
    return ExchangeRate.objects.exists()


def usd_to_lyd(amount_usd, rate=None):
    """Convert a USD amount to LYD, rounded to 2 dp. ``None`` -> ``None``."""
    if amount_usd is None:
        return None
    rate = get_current_rate() if rate is None else Decimal(rate)
    return (Decimal(amount_usd) * rate).quantize(LYD_QUANT, rounding=ROUND_HALF_UP)


def lyd_to_usd(amount_lyd, rate=None):
    """Convert an LYD amount back to USD, rounded to 2 dp. ``None`` -> ``None``."""
    if amount_lyd is None:
        return None
    rate = get_current_rate() if rate is None else Decimal(rate)
    if rate == 0:
        return None
    return (Decimal(amount_lyd) / rate).quantize(USD_QUANT, rounding=ROUND_HALF_UP)


def quantize_lyd(amount):
    """Normalise an arbitrary Decimal to 2-dp LYD money."""
    return Decimal(amount or 0).quantize(LYD_QUANT, rounding=ROUND_HALF_UP)
