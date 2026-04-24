from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from catalog.models import CardVariant
from common.models import TimeStampedModel


class InventoryItem(TimeStampedModel):
    class Condition(models.TextChoices):
        MINT = "MINT", "Mint"
        NEAR_MINT = "NEAR_MINT", "Near Mint"
        LIGHTLY_PLAYED = "LIGHTLY_PLAYED", "Lightly Played"
        MODERATELY_PLAYED = "MODERATELY_PLAYED", "Moderately Played"
        HEAVILY_PLAYED = "HEAVILY_PLAYED", "Heavily Played"
        DAMAGED = "DAMAGED", "Damaged"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="inventory_items",
    )
    card_variant = models.ForeignKey(
        CardVariant,
        on_delete=models.CASCADE,
        related_name="inventory_items",
    )
    condition = models.CharField(max_length=40, choices=Condition.choices)
    quantity = models.PositiveIntegerField()
    reserved_quantity = models.PositiveIntegerField(default=0)
    acquired_at = models.DateField(default=timezone.localdate)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        db_table = "inventory_item"
        ordering = ("owner_id", "card_variant_id", "condition")
        indexes = [
            models.Index(fields=("owner", "card_variant"), name="inventory_owner_variant_idx"),
            models.Index(
                fields=("owner", "card_variant", "condition"),
                name="inventory_active_owner_idx",
                condition=models.Q(quantity__gt=0),
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=("owner", "card_variant", "condition"),
                name="unique_inventory_owner_variant_condition",
            ),
            models.CheckConstraint(condition=models.Q(quantity__gte=0), name="inventory_quantity_non_negative"),
            models.CheckConstraint(
                condition=models.Q(reserved_quantity__gte=0),
                name="inventory_reserved_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(reserved_quantity__lte=models.F("quantity")),
                name="inventory_reserved_not_above_quantity",
            ),
            models.CheckConstraint(
                condition=models.Q(purchase_price__isnull=True) | models.Q(purchase_price__gte=0),
                name="inventory_purchase_price_non_negative",
            ),
        ]

    @property
    def available_quantity(self):
        return self.quantity - self.reserved_quantity

    def clean(self):
        super().clean()
        if self.quantity < 0:
            raise ValidationError({"quantity": "Quantity cannot be negative."})
        if self.reserved_quantity < 0:
            raise ValidationError({"reserved_quantity": "Reserved quantity cannot be negative."})
        if self.reserved_quantity > self.quantity:
            raise ValidationError({"reserved_quantity": "Reserved quantity cannot exceed quantity."})
        if self.purchase_price is not None and self.purchase_price < 0:
            raise ValidationError({"purchase_price": "Purchase price cannot be negative."})

    def __str__(self):
        return f"{self.owner} owns {self.quantity} x {self.card_variant}"


class InventoryHistory(models.Model):
    class ChangeType(models.TextChoices):
        ADD = "ADD", "Add"
        INCREASE = "INCREASE", "Increase"
        DECREASE = "DECREASE", "Decrease"
        RESERVE = "RESERVE", "Reserve"
        RELEASE = "RELEASE", "Release"
        PURCHASE = "PURCHASE", "Purchase"
        ADJUST = "ADJUST", "Adjust"

    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.CASCADE,
        related_name="history_entries",
    )
    change_type = models.CharField(max_length=40, choices=ChangeType.choices)
    quantity_delta = models.IntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventory_history_entries",
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "inventory_history"
        ordering = ("-created_at", "id")
        indexes = [
            models.Index(fields=("inventory_item", "created_at"), name="history_item_created_idx"),
            models.Index(fields=("created_by", "created_at"), name="history_actor_created_idx"),
        ]

    def __str__(self):
        return f"{self.change_type} {self.quantity_delta} for inventory item {self.inventory_item_id}"
