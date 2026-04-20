from django.core.exceptions import ValidationError
from django.db import transaction

from inventory.models import InventoryHistory, InventoryItem


def add_inventory_item(
    *,
    owner,
    card_variant,
    condition,
    quantity,
    actor=None,
    purchase_price=None,
    note="",
):
    _validate_positive_quantity(quantity)

    with transaction.atomic():
        item, created = InventoryItem.objects.select_for_update().get_or_create(
            owner=owner,
            card_variant=card_variant,
            condition=condition,
            defaults={
                "quantity": quantity,
                "purchase_price": purchase_price,
            },
        )
        if created:
            item.full_clean()
            item.save()
            _write_history(
                item=item,
                change_type=InventoryHistory.ChangeType.ADD,
                quantity_delta=quantity,
                actor=actor,
                note=note,
            )
            return item

        item.quantity += quantity
        if purchase_price is not None:
            item.purchase_price = purchase_price
        item.full_clean()
        item.save(update_fields=("quantity", "purchase_price", "updated_at"))
        _write_history(
            item=item,
            change_type=InventoryHistory.ChangeType.INCREASE,
            quantity_delta=quantity,
            actor=actor,
            note=note,
        )
        return item


def increase_quantity(*, item, quantity, actor=None, note=""):
    _validate_positive_quantity(quantity)

    with transaction.atomic():
        item = _lock_item(item)
        item.quantity += quantity
        item.full_clean()
        item.save(update_fields=("quantity", "updated_at"))
        _write_history(
            item=item,
            change_type=InventoryHistory.ChangeType.INCREASE,
            quantity_delta=quantity,
            actor=actor,
            note=note,
        )
        return item


def decrease_quantity(*, item, quantity, actor=None, note=""):
    _validate_positive_quantity(quantity)

    with transaction.atomic():
        item = _lock_item(item)
        if quantity > item.available_quantity:
            raise ValidationError("Cannot decrease more than the available quantity.")

        item.quantity -= quantity
        item.full_clean()
        item.save(update_fields=("quantity", "updated_at"))
        _write_history(
            item=item,
            change_type=InventoryHistory.ChangeType.DECREASE,
            quantity_delta=-quantity,
            actor=actor,
            note=note,
        )
        return item


def reserve_quantity(*, item, quantity, actor=None, note=""):
    _validate_positive_quantity(quantity)

    with transaction.atomic():
        item = _lock_item(item)
        if quantity > item.available_quantity:
            raise ValidationError("Cannot reserve more than the available quantity.")

        item.reserved_quantity += quantity
        item.full_clean()
        item.save(update_fields=("reserved_quantity", "updated_at"))
        _write_history(
            item=item,
            change_type=InventoryHistory.ChangeType.RESERVE,
            quantity_delta=quantity,
            actor=actor,
            note=note,
        )
        return item


def release_reserved_quantity(*, item, quantity, actor=None, note=""):
    _validate_positive_quantity(quantity)

    with transaction.atomic():
        item = _lock_item(item)
        if quantity > item.reserved_quantity:
            raise ValidationError("Cannot release more than the reserved quantity.")

        item.reserved_quantity -= quantity
        item.full_clean()
        item.save(update_fields=("reserved_quantity", "updated_at"))
        _write_history(
            item=item,
            change_type=InventoryHistory.ChangeType.RELEASE,
            quantity_delta=-quantity,
            actor=actor,
            note=note,
        )
        return item


def merge_purchased_item(
    *,
    buyer,
    card_variant,
    condition,
    quantity,
    actor=None,
    purchase_price=None,
    note="Purchased from marketplace",
):
    _validate_positive_quantity(quantity)

    with transaction.atomic():
        item, created = InventoryItem.objects.select_for_update().get_or_create(
            owner=buyer,
            card_variant=card_variant,
            condition=condition,
            defaults={
                "quantity": quantity,
                "purchase_price": purchase_price,
            },
        )
        if not created:
            item.quantity += quantity
            if purchase_price is not None:
                item.purchase_price = purchase_price

        item.full_clean()
        item.save()
        _write_history(
            item=item,
            change_type=InventoryHistory.ChangeType.PURCHASE,
            quantity_delta=quantity,
            actor=actor,
            note=note,
        )
        return item


def _lock_item(item):
    return InventoryItem.objects.select_for_update().get(pk=item.pk)


def _validate_positive_quantity(quantity):
    if quantity <= 0:
        raise ValidationError("Quantity must be greater than zero.")


def _write_history(*, item, change_type, quantity_delta, actor=None, note=""):
    return InventoryHistory.objects.create(
        inventory_item=item,
        change_type=change_type,
        quantity_delta=quantity_delta,
        created_by=actor,
        note=note,
    )
