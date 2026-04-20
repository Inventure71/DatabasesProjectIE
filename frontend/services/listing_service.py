from catalog.models import CardGame
from marketplace.models import MarketListing

from .catalog_service import RARITIES, _getlist, _maximum_price, _minimum_price, _variant_to_frontend_card


def list_listings(params):
    listings = _active_listing_queryset()
    query = params.get("q", "").strip()
    game = params.get("game", "")
    selected_rarities = [rarity for rarity in _getlist(params, "rarity") if rarity]
    min_price = _minimum_price(params)
    max_price = _maximum_price(params)

    if query:
        listings = listings.filter(inventory_item__card_variant__card__name__icontains=query)
    if game:
        listings = listings.filter(inventory_item__card_variant__card__game__name=game)
    if selected_rarities:
        listings = listings.filter(inventory_item__card_variant__rarity__in=selected_rarities)
    if min_price is not None:
        listings = listings.filter(unit_price__gte=min_price)
    if max_price is not None:
        listings = listings.filter(unit_price__lte=max_price)

    sort = params.get("sort", "newest")
    if sort == "price_asc":
        listings = listings.order_by("unit_price", "id")
    elif sort == "price_desc":
        listings = listings.order_by("-unit_price", "id")
    elif sort == "name":
        listings = listings.order_by("inventory_item__card_variant__card__name", "id")
    else:
        listings = listings.order_by("-created_at", "id")

    return [_listing_to_frontend_listing(listing) for listing in listings]


def get_listing(listing_id):
    listing = _active_listing_queryset().filter(pk=listing_id).first()
    if listing is None:
        return None
    return _listing_to_frontend_listing(listing)


def get_listing_facets():
    active_listings = _active_listing_queryset()
    return {
        "games": list(CardGame.objects.order_by("name").values_list("name", flat=True)),
        "rarities": RARITIES,
        "total_listings": active_listings.count(),
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
    )


def _listing_to_frontend_listing(listing):
    variant = listing.inventory_item.card_variant
    return {
        "id": listing.id,
        "seller": {"id": listing.seller_id, "username": listing.seller.username},
        "card": _variant_to_frontend_card(variant),
        "condition": listing.inventory_item.condition,
        "quantity": listing.quantity_available,
        "price_per_unit": listing.unit_price,
        "currency": listing.currency,
    }
