from django.core.exceptions import ValidationError
from django.http import Http404

from catalog.models import CardVariant
from inventory.models import InventoryItem
from inventory.serializers import InventoryItemSerializer
from inventory.services import (
    add_inventory_item,
    decrease_quantity,
    increase_quantity,
    release_reserved_quantity,
    reserve_quantity,
)
from marketplace.models import MarketListing, PurchaseOrder, PurchaseOrderLine
from marketplace.serializers import MarketListingSerializer, PurchaseOrderSerializer
from marketplace.services import purchase_listing
from pricing.serializers import CollectionValueSerializer, PriceSnapshotSerializer
from pricing.services import estimate_collection_value, get_variant_price_history
from users.serializers import CurrentUserSerializer


def get_current_user(user):
    return CurrentUserSerializer(user).data


def list_my_inventory(user):
    queryset = _user_inventory_queryset(user)
    return InventoryItemSerializer(queryset, many=True).data


def add_inventory_item_for_user(*, user, card_variant_id, condition, quantity, purchase_price=None):
    variant = _get_card_variant(card_variant_id)
    item = add_inventory_item(
        owner=user,
        card_variant=variant,
        condition=condition,
        quantity=quantity,
        purchase_price=purchase_price,
        actor=user,
        note="Added from frontend",
    )
    return InventoryItemSerializer(item).data


def update_inventory_item_for_user(*, user, item_id, action, quantity):
    item = _get_user_inventory_item(user=user, item_id=item_id)
    if action == "INCREASE":
        item = increase_quantity(item=item, quantity=quantity, actor=user)
    elif action == "DECREASE":
        item = decrease_quantity(item=item, quantity=quantity, actor=user)
    elif action == "RESERVE":
        item = reserve_quantity(item=item, quantity=quantity, actor=user)
    elif action == "RELEASE":
        item = release_reserved_quantity(item=item, quantity=quantity, actor=user)
    else:
        raise ValidationError("Unsupported inventory action.")

    return InventoryItemSerializer(item).data


def remove_inventory_quantity_for_user(*, user, item_id, quantity):
    item = _get_user_inventory_item(user=user, item_id=item_id)
    item = decrease_quantity(
        item=item,
        quantity=quantity,
        actor=user,
        note="Removed from frontend",
    )
    return InventoryItemSerializer(item).data


def list_marketplace_listings(params=None):
    queryset = _active_listing_queryset()
    params = params or {}

    seller = params.get("seller")
    card_variant = params.get("card_variant")
    status = params.get("status")
    price_min = params.get("price_min") or params.get("min_price")
    price_max = params.get("price_max") or params.get("max_price")

    if seller:
        queryset = queryset.filter(seller_id=seller)
    if card_variant:
        queryset = queryset.filter(inventory_item__card_variant_id=card_variant)
    if status and status != MarketListing.Status.ACTIVE:
        queryset = queryset.none()
    if price_min:
        queryset = queryset.filter(unit_price__gte=price_min)
    if price_max:
        queryset = queryset.filter(unit_price__lte=price_max)

    return MarketListingSerializer(queryset, many=True).data


def get_marketplace_listing(listing_id):
    listing = _active_listing_queryset().filter(pk=listing_id).first()
    if listing is None:
        raise Http404("Listing not found.")
    return MarketListingSerializer(listing).data


def buy_marketplace_listing(*, user, listing_id, quantity):
    listing = MarketListing.objects.get(pk=listing_id)
    order = purchase_listing(buyer=user, listing=listing, quantity=quantity)
    order = _order_history_queryset().get(pk=order.pk)
    return PurchaseOrderSerializer(order).data


def list_my_sales(user):
    queryset = _order_history_queryset().filter(seller=user)
    return PurchaseOrderSerializer(queryset, many=True).data


def list_my_purchases(user):
    queryset = _order_history_queryset().filter(buyer=user)
    return PurchaseOrderSerializer(queryset, many=True).data


def list_variant_price_history(variant_id):
    variant = _get_card_variant(variant_id)
    queryset = get_variant_price_history(card_variant=variant)
    return PriceSnapshotSerializer(queryset, many=True).data


def get_collection_value(user):
    data = {
        "total_value": estimate_collection_value(owner=user),
        "currency": "EUR",
    }
    return CollectionValueSerializer(data).data


def _get_card_variant(card_variant_id):
    variant = CardVariant.objects.filter(pk=card_variant_id).first()
    if variant is None:
        raise Http404("Card variant not found.")
    return variant


def _get_user_inventory_item(*, user, item_id):
    item = _user_inventory_queryset(user).filter(pk=item_id).first()
    if item is None:
        raise Http404("Inventory item not found.")
    return item


def _user_inventory_queryset(user):
    return (
        InventoryItem.objects.filter(owner=user)
        .select_related("card_variant__card", "card_variant__set")
        .order_by("card_variant__card__name", "condition")
    )


def _active_listing_queryset():
    return (
        MarketListing.objects.filter(
            status=MarketListing.Status.ACTIVE,
            quantity_available__gt=0,
        )
        .select_related(
            "seller",
            "inventory_item__card_variant__card__game",
            "inventory_item__card_variant__set",
            "inventory_item__card_variant__image",
        )
        .order_by("-created_at", "id")
    )


def _order_history_queryset():
    line_queryset = PurchaseOrderLine.objects.select_related(
        "listing",
        "card_variant__card",
        "card_variant__set",
    )
    return (
        PurchaseOrder.objects.select_related("buyer", "seller")
        .prefetch_related("lines")
        .prefetch_related("lines__card_variant__card", "lines__card_variant__set")
        .order_by("-created_at", "id")
    )
