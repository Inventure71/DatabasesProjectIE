from decimal import Decimal

from django.contrib.postgres.search import TrigramSimilarity
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, Exists, ExpressionWrapper, F, OuterRef, Prefetch, Sum, Value
from django.db.models.functions import Coalesce, Greatest
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
from marketplace.services import create_listing, purchase_listing
from pricing.serializers import CollectionValueSerializer, PriceSnapshotSerializer
from pricing.services import estimate_collection_value, get_variant_price_history
from users.serializers import CurrentUserSerializer


COLLECTION_BROWSER_PAGE_SIZE = 12
SEARCH_SIMILARITY_THRESHOLD = 0.1
ZERO_MONEY = Value(Decimal("0"), output_field=DecimalField(max_digits=12, decimal_places=2))


def get_current_user(user):
    return CurrentUserSerializer(user).data


def list_my_inventory(user):
    queryset = _user_inventory_queryset(user)
    return [_inventory_item_to_frontend(item) for item in queryset]


def list_my_inventory_page(user, params, *, page_size=COLLECTION_BROWSER_PAGE_SIZE):
    queryset = _filter_user_inventory_queryset(user, params)
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(params.get("page"))

    return {
        "results": [_inventory_item_to_frontend(item) for item in page_obj.object_list],
        "count": paginator.count,
        "page": page_obj.number,
        "page_size": page_size,
        "num_pages": paginator.num_pages,
        "has_previous": page_obj.has_previous(),
        "has_next": page_obj.has_next(),
        "previous_page_number": page_obj.previous_page_number() if page_obj.has_previous() else None,
        "next_page_number": page_obj.next_page_number() if page_obj.has_next() else None,
    }


def get_inventory_summary(user):
    return _user_inventory_base_queryset(user).aggregate(
        total_quantity=Coalesce(Sum("quantity"), 0),
        available_quantity=Coalesce(Sum(F("quantity") - F("reserved_quantity")), 0),
        reserved_quantity=Coalesce(Sum("reserved_quantity"), 0),
    )


def list_collection_set_summaries(user, params):
    queryset = _filter_user_inventory_queryset(user, params).order_by()
    row_value = ExpressionWrapper(
        F("quantity") * F("card_variant__current_value"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )
    rows = list(
        queryset.values(
            "card_variant__set_id",
            "card_variant__set__name",
            "card_variant__card__game__name",
        )
        .annotate(
            record_count=Count("id"),
            unit_count=Coalesce(Sum("quantity"), 0),
            total_value=Coalesce(Sum(row_value), ZERO_MONEY),
        )
        .order_by("card_variant__card__game__name", "card_variant__set__name")
    )
    cover_cards = _inventory_cover_cards_by_set(user, params, [row["card_variant__set_id"] for row in rows])

    return [
        {
            "set_name": row["card_variant__set__name"],
            "game": row["card_variant__card__game__name"],
            "cover_card": cover_cards.get(row["card_variant__set_id"]),
            "record_count": row["record_count"],
            "unit_count": row["unit_count"],
            "total_value": row["total_value"],
            "query": _query_with(params, view="card", set=row["card_variant__set__name"], page=None),
            "is_active": params.get("set", "") == row["card_variant__set__name"],
        }
        for row in rows
    ]


def list_collection_game_summaries(user, params):
    queryset = _filter_user_inventory_queryset(user, params).order_by()
    row_value = ExpressionWrapper(
        F("quantity") * F("card_variant__current_value"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )
    rows = list(
        queryset.values("card_variant__card__game__name")
        .annotate(
            set_count=Count("card_variant__set_id", distinct=True),
            record_count=Count("id"),
            unit_count=Coalesce(Sum("quantity"), 0),
            total_value=Coalesce(Sum(row_value), ZERO_MONEY),
        )
        .order_by("card_variant__card__game__name")
    )
    cover_cards = _inventory_cover_cards_by_game(user, params, [row["card_variant__card__game__name"] for row in rows])

    return [
        {
            "game": row["card_variant__card__game__name"],
            "cover_card": cover_cards.get(row["card_variant__card__game__name"]),
            "set_count": row["set_count"],
            "record_count": row["record_count"],
            "unit_count": row["unit_count"],
            "total_value": row["total_value"],
            "query": _query_with(params, view="set", game=row["card_variant__card__game__name"], set=None, page=None),
            "is_active": params.get("game", "") == row["card_variant__card__game__name"],
        }
        for row in rows
    ]


def list_my_inventory_for_variant(user, variant_id):
    queryset = _user_inventory_queryset(user).filter(card_variant_id=variant_id)
    return [_inventory_item_to_frontend(item) for item in queryset]


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


def list_my_active_listings(user):
    queryset = _active_listing_queryset().filter(seller=user)
    return [_listing_to_frontend_listing(listing) for listing in queryset]


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


def create_marketplace_listing_for_user(*, user, inventory_item_id, quantity, unit_price, currency="EUR"):
    inventory_item = _get_user_inventory_item(user=user, item_id=inventory_item_id)
    listing = create_listing(
        seller=user,
        inventory_item=inventory_item,
        quantity=quantity,
        unit_price=unit_price,
        currency=currency,
    )
    listing = _listing_queryset().get(pk=listing.pk)
    return MarketListingSerializer(listing).data


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
    active_listing_prefetch = Prefetch(
        "market_listings",
        queryset=MarketListing.objects.filter(
            status=MarketListing.Status.ACTIVE,
            quantity_available__gt=0,
        ).order_by("id"),
        to_attr="active_frontend_listings",
    )
    return (
        _user_inventory_base_queryset(user)
        .select_related("card_variant__card__game", "card_variant__set", "card_variant__image")
        .prefetch_related(active_listing_prefetch)
        .order_by("card_variant__card__name", "condition")
    )


def _user_inventory_base_queryset(user):
    return InventoryItem.objects.filter(owner=user, quantity__gt=0)


def _filter_user_inventory_queryset(user, params):
    queryset = _user_inventory_queryset(user)
    query = params.get("q", "").strip()
    game = params.get("game", "")
    set_name = params.get("set", "")
    language = params.get("language", "")
    selected_rarities = [rarity for rarity in _getlist(params, "rarity") if rarity]
    selected_my_listings = params.get("my_listings", "")
    min_price = params.get("min_price", "")
    max_price = params.get("max_price", "")

    if query:
        queryset = (
            queryset.annotate(search_rank=_inventory_search_rank(query))
            .filter(search_rank__gt=SEARCH_SIMILARITY_THRESHOLD)
            .order_by("-search_rank", "card_variant__card__name", "condition")
        )
    if game:
        queryset = queryset.filter(card_variant__card__game__name=game)
    if set_name:
        queryset = queryset.filter(card_variant__set__name=set_name)
    if language:
        queryset = queryset.filter(card_variant__language=language)
    if selected_rarities:
        queryset = queryset.filter(card_variant__rarity__in=selected_rarities)
    if min_price:
        queryset = queryset.filter(card_variant__current_value__gte=min_price)
    if max_price:
        queryset = queryset.filter(card_variant__current_value__lte=max_price)
    if selected_my_listings == "listed":
        active_listing = MarketListing.objects.filter(
            inventory_item=OuterRef("pk"),
            status=MarketListing.Status.ACTIVE,
            quantity_available__gt=0,
        )
        queryset = queryset.annotate(has_active_listing_filter=Exists(active_listing)).filter(
            has_active_listing_filter=True
        )

    return queryset


def _inventory_item_to_frontend(item):
    data = InventoryItemSerializer(item).data
    variant = item.card_variant
    try:
        image = variant.image
    except CardVariant.image.RelatedObjectDoesNotExist:
        image = None

    data["condition_label"] = item.get_condition_display()
    data["card"] = {
        "id": variant.card_id,
        "variant_id": variant.id,
        "name": variant.card.name,
        "game": variant.card.game.name,
        "set_name": variant.set.name,
        "rarity": variant.rarity,
        "finish": variant.finish,
        "language": variant.language,
        "current_value": variant.current_value,
        "image_url": image.image_url if image else "",
    }
    data["estimated_value"] = variant.current_value * item.quantity
    active_listings = getattr(item, "active_frontend_listings", None)
    if active_listings is None:
        active_listings = item.market_listings.filter(
            status=MarketListing.Status.ACTIVE,
            quantity_available__gt=0,
        ).order_by("id")
    data["active_listings"] = [
        {
            "id": listing.id,
            "quantity": listing.quantity,
            "quantity_available": listing.quantity_available,
            "price_per_unit": listing.unit_price,
            "currency": listing.currency,
            "status": listing.status,
        }
        for listing in active_listings
    ]
    data["listed_quantity"] = sum(listing["quantity_available"] for listing in data["active_listings"])
    data["has_active_listings"] = data["listed_quantity"] > 0
    if data["listed_quantity"] >= item.quantity:
        data["listing_state"] = "fully_listed"
    elif data["listed_quantity"]:
        data["listing_state"] = "partially_listed"
    else:
        data["listing_state"] = "unlisted"
    return data


def _inventory_cover_cards_by_set(user, params, set_ids):
    covers = {}
    if not set_ids:
        return covers
    items = (
        _filter_user_inventory_queryset(user, params)
        .filter(card_variant__set_id__in=set_ids)
        .order_by("card_variant__set_id", "card_variant__card__name", "id")
        .distinct("card_variant__set_id")
    )
    for item in items:
        covers.setdefault(item.card_variant.set_id, _inventory_item_to_frontend(item)["card"])
    return covers


def _inventory_cover_cards_by_game(user, params, games):
    covers = {}
    if not games:
        return covers
    items = (
        _filter_user_inventory_queryset(user, params)
        .filter(card_variant__card__game__name__in=games)
        .order_by("card_variant__card__game__name", "card_variant__card__name", "id")
        .distinct("card_variant__card__game__name")
    )
    for item in items:
        covers.setdefault(item.card_variant.card.game.name, _inventory_item_to_frontend(item)["card"])
    return covers


def _inventory_search_rank(query):
    return Greatest(
        TrigramSimilarity("card_variant__card__name", query),
        TrigramSimilarity("card_variant__card__card_type", query),
        TrigramSimilarity("card_variant__card__subtype", query),
        TrigramSimilarity("card_variant__collector_number", query),
        TrigramSimilarity("card_variant__edition_label", query),
    )


def _getlist(params, name):
    if hasattr(params, "getlist"):
        return params.getlist(name)
    value = params.get(name, [])
    return value if isinstance(value, list) else [value]


def _query_with(params, **updates):
    query = params.copy()
    for key, value in updates.items():
        if value in (None, ""):
            query.pop(key, None)
        else:
            query[key] = value
    return query.urlencode()


def _listing_queryset():
    return MarketListing.objects.select_related(
        "seller",
        "inventory_item__card_variant__card",
        "inventory_item__card_variant__set",
    )


def _listing_to_frontend_listing(listing):
    variant = listing.inventory_item.card_variant
    try:
        image = variant.image
    except CardVariant.image.RelatedObjectDoesNotExist:
        image = None

    return {
        "id": listing.id,
        "seller": {"id": listing.seller_id, "username": listing.seller.username},
        "card": {
            "id": variant.card_id,
            "variant_id": variant.id,
            "name": variant.card.name,
            "game": variant.card.game.name,
            "set_name": variant.set.name,
            "rarity": variant.rarity,
            "finish": variant.finish,
            "language": variant.language,
            "current_value": variant.current_value,
            "image_url": image.image_url if image else "",
        },
        "condition": listing.inventory_item.get_condition_display(),
        "status": listing.status,
        "quantity": listing.quantity,
        "quantity_available": listing.quantity_available,
        "price_per_unit": listing.unit_price,
        "currency": listing.currency,
    }


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
