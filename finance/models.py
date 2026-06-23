"""
Finance domain models.

This app is the monetary foundation of the system. Everything that needs to
convert between USD (how Switch imports & thinks about cost) and LYD (how Switch
sells locally) reuses the single global black-market exchange rate defined here.

Layering: ``finance`` has no dependency on ``catalog`` or ``sales`` — they depend
on it. Keep it that way.
"""
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from dlux.models import ScopedModel

# Cache key for the live USD->LYD rate. Invalidated whenever a new rate is saved.
CURRENT_RATE_CACHE_KEY = "finance:current_usd_lyd_rate"
CURRENT_RATE_CACHE_TTL = 60 * 60  # 1h; bounded by explicit invalidation on save.


class ExchangeRate(ScopedModel):
    """Append-only history of the USD -> LYD conversion rate.

    The newest row is the *live* rate used everywhere prices are computed. Past
    rows are never edited, so the system keeps a full audit trail of how the
    black-market rate moved over time (``created_at`` / ``created_by`` come from
    ``ScopedModel``). Invoices freeze their own copy of the rate, so editing or
    adding a rate here never rewrites historical invoice totals.
    """

    SOURCE_BLACK_MARKET = "black_market"
    SOURCE_OFFICIAL = "official"
    SOURCE_CUSTOM = "custom"
    SOURCE_CHOICES = (
        (SOURCE_BLACK_MARKET, "Black Market"),
        (SOURCE_OFFICIAL, "Official"),
        (SOURCE_CUSTOM, "Custom"),
    )

    rate = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0.0001"))],
        verbose_name="LYD per 1 USD",
        help_text="How many Libyan Dinars equal one US Dollar.",
    )
    source = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default=SOURCE_BLACK_MARKET,
        verbose_name="Source",
    )
    note = models.CharField(max_length=255, blank=True, verbose_name="Note")

    class Meta:
        verbose_name = "Exchange Rate"
        verbose_name_plural = "Exchange Rates"
        ordering = ["-created_at"]
        permissions = [("manage_exchangerate", "Can set the global exchange rate")]

    def __str__(self):
        return f"1 USD = {self.rate} LYD"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # The newest row is authoritative; refresh the cached live rate.
        if not self.deleted_at:
            cache.set(CURRENT_RATE_CACHE_KEY, self.rate, CURRENT_RATE_CACHE_TTL)


class CashDeposit(ScopedModel):
    """A cash hand-over recorded by a staff member (ايداع نقدي).

    Technicians and delivery reps record the money they collected; an admin then
    confirms it. Payments on invoices may optionally point at the deposit that
    carried their cash, so the books reconcile.
    """

    METHOD_CASH = "cash"
    METHOD_BANK = "bank_transfer"
    METHOD_CHEQUE = "cheque"
    METHOD_CHOICES = (
        (METHOD_CASH, "Cash"),
        (METHOD_BANK, "Bank Transfer"),
        (METHOD_CHEQUE, "Cheque"),
    )

    STATUS_PENDING = "pending"
    STATUS_CONFIRMED = "confirmed"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pending"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_REJECTED, "Rejected"),
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        verbose_name="Amount (LYD)",
    )
    method = models.CharField(
        max_length=20, choices=METHOD_CHOICES, default=METHOD_CASH, verbose_name="Method"
    )
    reference = models.CharField(max_length=120, blank=True, verbose_name="Reference")
    deposited_at = models.DateField(default=timezone.localdate, verbose_name="Deposit Date")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True,
        verbose_name="Status",
    )
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="confirmed_cash_deposits",
        on_delete=models.SET_NULL,
        editable=False,
        verbose_name="Confirmed By",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True, editable=False, verbose_name="Confirmed At")
    notes = models.TextField(blank=True, verbose_name="Notes")

    class Meta:
        verbose_name = "Cash Deposit"
        verbose_name_plural = "Cash Deposits"
        ordering = ["-deposited_at", "-created_at"]
        permissions = [("confirm_cashdeposit", "Can confirm or reject cash deposits")]

    def __str__(self):
        return f"{self.amount} LYD ({self.get_status_display()})"

    def confirm(self, actor):
        self.status = self.STATUS_CONFIRMED
        self.confirmed_by = actor
        self.confirmed_at = timezone.now()
        self.save(update_fields=["status", "confirmed_by", "confirmed_at", "updated_at"])

    def reject(self, actor):
        self.status = self.STATUS_REJECTED
        self.confirmed_by = actor
        self.confirmed_at = timezone.now()
        self.save(update_fields=["status", "confirmed_by", "confirmed_at", "updated_at"])
