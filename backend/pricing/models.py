from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from catalog.models import CardVariant
from common.models import TimeStampedModel


class PriceSnapshot(TimeStampedModel):
    card_variant = models.ForeignKey(
        CardVariant,
        on_delete=models.CASCADE,
        related_name="price_snapshots",
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="EUR")
    source_name = models.CharField(max_length=120)
    captured_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "price_snapshot"
        ordering = ("-captured_at", "-id")
        indexes = [
            models.Index(fields=("card_variant", "captured_at"), name="price_variant_captured_idx"),
            models.Index(fields=("source_name", "captured_at"), name="price_source_captured_idx"),
            models.Index(fields=("card_variant", "-captured_at", "-id"), name="price_variant_latest_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gte=0), name="price_snapshot_price_non_negative"),
        ]

    def clean(self):
        super().clean()
        if self.price < 0:
            raise ValidationError({"price": "Price cannot be negative."})

    def __str__(self):
        return f"{self.card_variant} - {self.price} {self.currency} at {self.captured_at}"
