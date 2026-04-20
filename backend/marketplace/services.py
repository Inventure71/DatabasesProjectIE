from django.core.exceptions import ValidationError
from django.db import transaction

from inventory.models import InventoryHistory, InventoryItem
from inventory.services import merge_purchased_item, release_reserved_quantity, reserve_quantity
from marketplace.models import MarketListing, PurchaseOrder, PurchaseOrderLine
from pricing.services import record_price_snapshot


def create_listing(*, seller, inventory_item, quantity, unit_price, currency="EUR"):
    _validate_positive_quantity(quantity)
    _validate_non_negative_price(unit_price)

    with transaction.atomic():
        inventory_item = _lock_inventory_item(inventory_item)
        if inventory_item.owner_id != seller.id:
            raise ValidationError("Cannot list inventory owned by another user.")
        if quantity > inventory_item.available_quantity:
            raise ValidationError("Cannot list more than the available inventory quantity.")

        reserve_quantity(
            item=inventory_item,
            quantity=quantity,
            actor=seller,
            note="Reserved for marketplace listing",
        )
        listing = MarketListing(
            seller=seller,
            inventory_item=inventory_item,
            quantity=quantity,
            quantity_available=quantity,
            unit_price=unit_price,
            currency=currency,
        )
        listing.full_clean()
        listing.save()
        return listing


def pause_listing(*, listing, seller):
    with transaction.atomic():
        listing = _lock_listing(listing)
        _validate_listing_seller(listing=listing, seller=seller)
        if listing.status != MarketListing.Status.ACTIVE:
            raise ValidationError("Only active listings can be paused.")

        listing.status = MarketListing.Status.PAUSED
        listing.full_clean()
        listing.save(update_fields=("status", "updated_at"))
        return listing


def cancel_listing(*, listing, seller):
    with transaction.atomic():
        listing = _lock_listing(listing)
        _validate_listing_seller(listing=listing, seller=seller)
        if listing.status not in (MarketListing.Status.ACTIVE, MarketListing.Status.PAUSED):
            raise ValidationError("Only active or paused listings can be cancelled.")

        quantity_to_release = listing.quantity_available
        if quantity_to_release:
            release_reserved_quantity(
                item=listing.inventory_item,
                quantity=quantity_to_release,
                actor=seller,
                note="Released from cancelled marketplace listing",
            )

        listing.status = MarketListing.Status.CANCELLED
        listing.quantity_available = 0
        listing.full_clean()
        listing.save(update_fields=("status", "quantity_available", "updated_at"))
        return listing


def mark_listing_sold_out(*, listing, seller):
    with transaction.atomic():
        listing = _lock_listing(listing)
        _validate_listing_seller(listing=listing, seller=seller)
        if listing.status not in (MarketListing.Status.ACTIVE, MarketListing.Status.PAUSED):
            raise ValidationError("Only active or paused listings can be marked sold out.")
        if listing.quantity_available != 0:
            raise ValidationError("Cannot mark a listing sold out while quantity is still available.")

        listing.status = MarketListing.Status.SOLD_OUT
        listing.full_clean()
        listing.save(update_fields=("status", "updated_at"))
        return listing


def purchase_listing(*, buyer, listing, quantity):
    _validate_positive_quantity(quantity)

    with transaction.atomic():
        listing = _lock_listing_for_purchase(listing)
        seller_inventory = _lock_inventory_item(listing.inventory_item)

        if buyer.id == listing.seller_id:
            raise ValidationError("Seller cannot buy their own listing.")
        if listing.status != MarketListing.Status.ACTIVE:
            raise ValidationError("Only active listings can be purchased.")
        if quantity > listing.quantity_available:
            raise ValidationError("Cannot purchase more than the available listing quantity.")
        if quantity > seller_inventory.reserved_quantity:
            raise ValidationError("Listing stock is not reserved correctly.")

        total_amount = listing.unit_price * quantity
        order = PurchaseOrder.objects.create(
            buyer=buyer,
            seller=listing.seller,
            status=PurchaseOrder.Status.PENDING,
            total_amount=total_amount,
            currency=listing.currency,
        )
        PurchaseOrderLine.objects.create(
            purchase_order=order,
            listing=listing,
            card_variant=seller_inventory.card_variant,
            quantity=quantity,
            unit_price=listing.unit_price,
        )

        seller_inventory.quantity -= quantity
        seller_inventory.reserved_quantity -= quantity
        seller_inventory.full_clean()
        seller_inventory.save(update_fields=("quantity", "reserved_quantity", "updated_at"))
        InventoryHistory.objects.create(
            inventory_item=seller_inventory,
            change_type=InventoryHistory.ChangeType.DECREASE,
            quantity_delta=-quantity,
            created_by=buyer,
            note="Sold through marketplace purchase",
        )

        merge_purchased_item(
            buyer=buyer,
            card_variant=seller_inventory.card_variant,
            condition=seller_inventory.condition,
            quantity=quantity,
            actor=buyer,
            purchase_price=listing.unit_price,
            note="Purchased through marketplace",
        )

        listing.quantity_available -= quantity
        if listing.quantity_available == 0:
            listing.status = MarketListing.Status.SOLD_OUT
        listing.full_clean()
        listing.save(update_fields=("quantity_available", "status", "updated_at"))

        order.status = PurchaseOrder.Status.COMPLETED
        order.full_clean()
        order.save(update_fields=("status", "updated_at"))
        record_price_snapshot(
            card_variant=seller_inventory.card_variant,
            price=listing.unit_price,
            currency=listing.currency,
            source_name="marketplace_sale",
            captured_at=order.created_at,
        )
        return order


def _lock_inventory_item(inventory_item):
    return InventoryItem.objects.select_for_update().get(pk=inventory_item.pk)


def _lock_listing(listing):
    return MarketListing.objects.select_for_update().select_related("inventory_item").get(pk=listing.pk)


def _lock_listing_for_purchase(listing):
    return (
        MarketListing.objects.select_for_update()
        .select_related("seller", "inventory_item", "inventory_item__card_variant")
        .get(pk=listing.pk)
    )


def _validate_listing_seller(*, listing, seller):
    if listing.seller_id != seller.id:
        raise ValidationError("Listing does not belong to this seller.")


def _validate_positive_quantity(quantity):
    if quantity <= 0:
        raise ValidationError("Quantity must be greater than zero.")


def _validate_non_negative_price(price):
    if price < 0:
        raise ValidationError("Unit price cannot be negative.")
