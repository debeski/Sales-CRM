"""
Catalog domain models — everything Switch can put on an invoice.

Two sellable families:
  * ``Product``  — stock items (smart locks, spare parts, unrelated goods).
  * ``Service``  — labour offerings (installation, maintenance, warranty, delivery).

Pricing model (decided with the owner): **hybrid USD base + optional LYD override**.
A product's price is held in USD (cost + markup, the way Switch imports), and the
LYD selling price is derived live from the global black-market rate in ``finance``.
Any item may carry a manual ``price_lyd_override`` for ad-hoc / unrelated goods.

``catalog`` depends on ``finance`` only (for the rate). It must never import
``sales`` — the stock ledger references invoices by their string number instead.
"""
from decimal import Decimal, ROUND_HALF_UP

from django.core.validators import MinValueValidator
from django.db import models

from dlux.models import ScopedModel

from finance.services import usd_to_lyd

TWO_PLACES = Decimal("0.01")


class Category(ScopedModel):
    """Grouping for products (e.g. Smart Locks, Spare Parts, Accessories)."""

    name = models.CharField(max_length=120, verbose_name="Name")
    description = models.TextField(blank=True, verbose_name="Description")
    is_active = models.BooleanField(default=True, verbose_name="Active")

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(ScopedModel):
    """A stock item. Priced in USD; sold in LYD via the live rate."""

    UNIT_PIECE = "piece"
    UNIT_BOX = "box"
    UNIT_SET = "set"
    UNIT_PAIR = "pair"
    UNIT_METER = "meter"
    UNIT_KG = "kg"
    UNIT_CHOICES = (
        (UNIT_PIECE, "Piece"),
        (UNIT_BOX, "Box"),
        (UNIT_SET, "Set"),
        (UNIT_PAIR, "Pair"),
        (UNIT_METER, "Meter"),
        (UNIT_KG, "Kg"),
    )

    sku = models.CharField(max_length=40, unique=True, blank=True, verbose_name="SKU")
    name = models.CharField(max_length=200, verbose_name="Name")
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.PROTECT,
        related_name="products", verbose_name="Category",
    )
    description = models.TextField(blank=True, verbose_name="Description")
    barcode = models.CharField(max_length=64, blank=True, db_index=True, verbose_name="Barcode")
    unit = models.CharField(max_length=12, choices=UNIT_CHOICES, default=UNIT_PIECE, verbose_name="Unit")

    # --- Pricing (USD base) ---
    cost_usd = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))], verbose_name="Import Cost (USD)",
    )
    markup_percent = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))], verbose_name="Markup %",
        help_text="Profit added on top of the import cost. Changing it recalculates the USD selling price.",
    )
    price_usd = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))], verbose_name="Selling Price (USD)",
        help_text="Auto-filled from cost + markup; edit it directly and the markup follows.",
    )
    price_lyd_override = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00"))], verbose_name="Manual LYD Price",
        help_text="Leave blank to sell at the live rate; enter a value to fix the LYD price for this item.",
    )

    # --- Stock ---
    track_stock = models.BooleanField(default=True, verbose_name="Track Stock")
    stock_qty = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"), verbose_name="Stock Qty",
    )
    reorder_level = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00"), verbose_name="Reorder Level",
    )

    is_active = models.BooleanField(default=True, verbose_name="Active")

    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ["name"]
        indexes = [models.Index(fields=["name"], name="catalog_product_name_idx")]

    def __str__(self):
        return f"{self.name} ({self.sku})" if self.sku else self.name

    def save(self, *args, **kwargs):
        # Persist the derived USD selling price so detail views and every
        # downstream read see a real number instead of 0 when the user only
        # entered cost + markup (the form JS normally fills this, but this keeps
        # the record consistent even for API/import/no-JS saves).
        if not self.price_usd or self.price_usd <= 0:
            derived = self.effective_price_usd
            if derived and derived > 0:
                self.price_usd = derived
        super().save(*args, **kwargs)
        if not self.sku:
            # SKU needs the pk, so assign on the next pass without re-running audit.
            self.sku = f"P{self.pk:05d}"
            super().save(update_fields=["sku"])

    def get_unit_display(self):
        """Translated unit label (dlux's generic detail view calls this directly,
        and Django's auto version would return the untranslated English choice)."""
        from common.i18n import t
        return t(f"unit_{self.unit}", dict(self.UNIT_CHOICES).get(self.unit, self.unit))

    @property
    def effective_price_usd(self):
        """USD selling price: explicit ``price_usd`` if set, else cost + markup."""
        if self.price_usd and self.price_usd > 0:
            return self.price_usd
        base = (self.cost_usd or Decimal("0")) * (Decimal("1") + (self.markup_percent or Decimal("0")) / Decimal("100"))
        return base.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    def selling_price_lyd(self, rate=None):
        """The LYD price shown to customers: manual override wins, else converted."""
        if self.price_lyd_override is not None:
            return self.price_lyd_override
        return usd_to_lyd(self.effective_price_usd, rate)

    def get_modal_context(self):
        """Extra rows for the dlux generic detail view. Surfaces the *effective*
        LYD selling price (live-converted unless a manual override is set) so the
        detail card matches the product list, whose price column is also derived."""
        from common.i18n import t
        price = self.selling_price_lyd()
        return {
            "extra_detail_fields": [
                {
                    "label": t("label_product_selling_price_lyd", "Selling Price (LYD)"),
                    "value": f"{price:,.2f}" if price is not None else "—",
                }
            ]
        }

    @property
    def is_low_stock(self):
        return self.track_stock and self.stock_qty <= self.reorder_level


class Service(ScopedModel):
    """A labour / after-sale offering. Priced in USD, LYD, or quoted per job."""

    TYPE_INSTALLATION = "installation"
    TYPE_MAINTENANCE = "maintenance"
    TYPE_WARRANTY = "warranty"
    TYPE_DELIVERY = "delivery"
    TYPE_OTHER = "other"
    TYPE_CHOICES = (
        (TYPE_INSTALLATION, "Installation"),
        (TYPE_MAINTENANCE, "Maintenance"),
        (TYPE_WARRANTY, "Warranty / After-sale"),
        (TYPE_DELIVERY, "Delivery"),
        (TYPE_OTHER, "Other"),
    )

    name = models.CharField(max_length=200, verbose_name="Name")
    service_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default=TYPE_INSTALLATION, db_index=True,
        verbose_name="Service Type",
    )
    description = models.TextField(blank=True, verbose_name="Description")
    price_usd = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00"))], verbose_name="Price (USD)",
    )
    price_lyd_override = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal("0.00"))], verbose_name="Manual LYD Price",
    )
    is_active = models.BooleanField(default=True, verbose_name="Active")

    class Meta:
        verbose_name = "Service"
        verbose_name_plural = "Services"
        ordering = ["service_type", "name"]

    def __str__(self):
        return self.name

    def get_service_type_display(self):
        """Translated service-type label (dlux's generic detail view calls this)."""
        from common.i18n import t
        return t(f"svctype_{self.service_type}", dict(self.TYPE_CHOICES).get(self.service_type, self.service_type))

    def selling_price_lyd(self, rate=None):
        """Override wins; else convert USD; else ``None`` meaning "quote per job"."""
        if self.price_lyd_override is not None:
            return self.price_lyd_override
        if self.price_usd is not None:
            return usd_to_lyd(self.price_usd, rate)
        return None

    def get_modal_context(self):
        """Effective LYD selling price for the dlux generic detail view (or the
        "Per job" marker when the service is quoted per job)."""
        from common.i18n import t
        price = self.selling_price_lyd()
        return {
            "extra_detail_fields": [
                {
                    "label": t("label_service_selling_price_lyd", "Selling Price (LYD)"),
                    "value": f"{price:,.2f}" if price is not None else t("ui_per_job", "Per job"),
                }
            ]
        }


class StockMovement(ScopedModel):
    """Append-style inventory ledger. Every change to ``Product.stock_qty`` is a row.

    Referenced invoices are stored by their string number (``reference``) so the
    catalog app stays independent of ``sales``.
    """

    TYPE_IN = "in"
    TYPE_OUT = "out"
    TYPE_ADJUST = "adjustment"
    TYPE_CHOICES = (
        (TYPE_IN, "Stock In"),
        (TYPE_OUT, "Stock Out"),
        (TYPE_ADJUST, "Adjustment"),
    )

    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="movements", verbose_name="Product"
    )
    movement_type = models.CharField(
        max_length=12, choices=TYPE_CHOICES, default=TYPE_IN, verbose_name="Type"
    )
    quantity = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Quantity",
        help_text="A positive amount for Stock In / Stock Out; a signed (+/-) amount for an Adjustment.",
    )
    reason = models.CharField(max_length=200, blank=True, verbose_name="Reason")
    reference = models.CharField(max_length=64, blank=True, db_index=True, verbose_name="Reference")

    class Meta:
        verbose_name = "Stock Movement"
        verbose_name_plural = "Stock Movements"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["product", "-created_at"], name="catalog_move_prod_idx")]

    def __str__(self):
        return f"{self.get_movement_type_display()} {self.quantity} × {self.product_id}"

    def get_movement_type_display(self):
        """Translated movement-type label (dlux's generic detail view calls this)."""
        from common.i18n import t
        return t(f"mtype_{self.movement_type}", dict(self.TYPE_CHOICES).get(self.movement_type, self.movement_type))

    @property
    def signed_quantity(self):
        if self.movement_type == self.TYPE_OUT:
            return -abs(self.quantity)
        if self.movement_type == self.TYPE_IN:
            return abs(self.quantity)
        return self.quantity  # adjustment: caller supplies the sign

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        # Apply the delta to the product on first insert only (ledger is append-only).
        if is_new and self.product.track_stock:
            Product.objects.filter(pk=self.product_id).update(
                stock_qty=models.F("stock_qty") + self.signed_quantity
            )
