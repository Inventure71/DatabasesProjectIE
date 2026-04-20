from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from catalog.models import CardVariant
from inventory.models import InventoryItem
from pricing.models import PriceSnapshot


def record_price_snapshot(
    *,
    card_variant,
    price,
    source_name,
    currency="EUR",
    captured_at=None,
    update_current_value=True,
):
    with transaction.atomic():
        snapshot = PriceSnapshot(
            card_variant=card_variant,
            price=price,
            currency=currency,
            source_name=source_name,
        )
        if captured_at is not None:
            snapshot.captured_at = captured_at

        snapshot.full_clean()
        snapshot.save()

        if update_current_value:
            update_current_value_from_latest_snapshot(card_variant=card_variant)

        return snapshot


def update_current_value_from_latest_snapshot(*, card_variant):
    with transaction.atomic():
        variant = CardVariant.objects.select_for_update().get(pk=card_variant.pk)
        latest_snapshot = PriceSnapshot.objects.filter(card_variant=variant).first()
        if latest_snapshot is None:
            raise ValidationError("Cannot update current value without price snapshots.")

        variant.current_value = latest_snapshot.price
        variant.full_clean()
        variant.save(update_fields=("current_value", "updated_at"))
        return variant


def get_variant_price_history(*, card_variant, limit=None):
    queryset = PriceSnapshot.objects.filter(card_variant=card_variant).select_related("card_variant")
    if limit is None:
        return queryset
    if limit <= 0:
        raise ValidationError("Limit must be greater than zero.")
    return queryset[:limit]


def estimate_collection_value(*, owner):
    total = Decimal("0.00")
    inventory_items = InventoryItem.objects.filter(owner=owner).select_related("card_variant")

    for item in inventory_items:
        total += item.card_variant.current_value * item.quantity

    return total
