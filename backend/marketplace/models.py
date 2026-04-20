from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from catalog.models import CardVariant
from common.models import TimeStampedModel
from inventory.models import InventoryItem


class MarketListing(TimeStampedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        PAUSED = "PAUSED", "Paused"
        SOLD_OUT = "SOLD_OUT", "Sold Out"
        CANCELLED = "CANCELLED", "Cancelled"

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="market_listings",
    )
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="market_listings",
    )
    status = models.CharField(max_length=40, choices=Status.choices, default=Status.ACTIVE)
    quantity = models.PositiveIntegerField()
    quantity_available = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="EUR")

    class Meta:
        db_table = "market_listing"
        ordering = ("-created_at", "id")
        indexes = [
            models.Index(fields=("seller", "status"), name="listing_seller_status_idx"),
            models.Index(fields=("status", "unit_price"), name="listing_status_price_idx"),
            models.Index(fields=("inventory_item", "status"), name="listing_inventory_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="listing_quantity_positive"),
            models.CheckConstraint(
                condition=models.Q(quantity_available__gte=0),
                name="listing_available_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity_available__lte=models.F("quantity")),
                name="listing_available_not_above_quantity",
            ),
            models.CheckConstraint(condition=models.Q(unit_price__gte=0), name="listing_price_non_negative"),
        ]

    def clean(self):
        super().clean()
        if self.inventory_item_id and self.seller_id and self.inventory_item.owner_id != self.seller_id:
            raise ValidationError({"inventory_item": "Listing inventory must belong to the seller."})
        if self.quantity <= 0:
            raise ValidationError({"quantity": "Listing quantity must be greater than zero."})
        if self.quantity_available < 0:
            raise ValidationError({"quantity_available": "Available quantity cannot be negative."})
        if self.quantity_available > self.quantity:
            raise ValidationError({"quantity_available": "Available quantity cannot exceed listing quantity."})
        if self.unit_price < 0:
            raise ValidationError({"unit_price": "Unit price cannot be negative."})
        if self.status == self.Status.SOLD_OUT and self.quantity_available != 0:
            raise ValidationError({"quantity_available": "Sold-out listings cannot have available quantity."})

    def __str__(self):
        return f"{self.inventory_item} listed by {self.seller}"


class PurchaseOrder(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        FAILED = "FAILED", "Failed"

    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="purchase_orders",
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sales_orders",
    )
    status = models.CharField(max_length=40, choices=Status.choices, default=Status.PENDING)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default="EUR")

    class Meta:
        db_table = "purchase_order"
        ordering = ("-created_at", "id")
        indexes = [
            models.Index(fields=("buyer", "status"), name="order_buyer_status_idx"),
            models.Index(fields=("seller", "status"), name="order_seller_status_idx"),
            models.Index(fields=("status", "created_at"), name="order_status_created_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(total_amount__gte=0), name="order_total_non_negative"),
            models.CheckConstraint(
                condition=~models.Q(buyer=models.F("seller")),
                name="order_buyer_not_seller",
            ),
        ]

    def clean(self):
        super().clean()
        if self.buyer_id and self.seller_id and self.buyer_id == self.seller_id:
            raise ValidationError({"buyer": "Buyer and seller must be different users."})
        if self.total_amount < 0:
            raise ValidationError({"total_amount": "Order total cannot be negative."})

    def __str__(self):
        return f"Order {self.pk or 'unsaved'} from {self.buyer} to {self.seller}"


class PurchaseOrderLine(TimeStampedModel):
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="lines",
    )
    listing = models.ForeignKey(
        MarketListing,
        on_delete=models.PROTECT,
        related_name="order_lines",
    )
    card_variant = models.ForeignKey(
        CardVariant,
        on_delete=models.PROTECT,
        related_name="purchase_order_lines",
    )
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "purchase_order_line"
        ordering = ("purchase_order_id", "id")
        indexes = [
            models.Index(fields=("purchase_order",), name="order_line_order_idx"),
            models.Index(fields=("listing",), name="order_line_listing_idx"),
            models.Index(fields=("card_variant",), name="order_line_variant_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name="order_line_quantity_positive"),
            models.CheckConstraint(condition=models.Q(unit_price__gte=0), name="order_line_price_non_negative"),
        ]

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    def clean(self):
        super().clean()
        if self.quantity <= 0:
            raise ValidationError({"quantity": "Order line quantity must be greater than zero."})
        if self.unit_price < 0:
            raise ValidationError({"unit_price": "Order line unit price cannot be negative."})
        if self.listing_id and self.card_variant_id:
            listing_variant_id = self.listing.inventory_item.card_variant_id
            if listing_variant_id != self.card_variant_id:
                raise ValidationError({"card_variant": "Order line card variant must match the listing."})
        if self.purchase_order_id and self.listing_id:
            if self.purchase_order.seller_id != self.listing.seller_id:
                raise ValidationError({"listing": "Order line listing must belong to the order seller."})

    def __str__(self):
        return f"{self.quantity} x {self.card_variant} for order {self.purchase_order_id}"
