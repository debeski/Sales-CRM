"""Celery tasks for the finance app."""
from celery import shared_task

from .services import refresh_cbl_rate_cache, refresh_ean_rate_cache


@shared_task(name="finance.tasks.refresh_market_rates")
def refresh_market_rates():
    """Refresh both external USD→LYD reference rates and cache them.

    Scheduled by Celery Beat (see config/celery.py). Each source is independent:
    if one site is unreachable the other still updates, and the previous cached
    value is preserved for the failing one.

    * official (CBL)        — cbl.gov.ly
    * black market (EAN)     — eanlibya.com
    """
    return {
        "cbl": refresh_cbl_rate_cache(),
        "ean": refresh_ean_rate_cache(),
    }
