from django.core.paginator import Paginator
from django.db.models import Exists, OuterRef
from django.utils import timezone

from catalog.models import Card, CardGame, CardSet, CardVariant
from marketplace.models import MarketListing, PurchaseOrder, PurchaseOrderLine
from pricing.models import PriceSnapshot

RARITIES = [choice[0] for choice in CardVariant.Rarity.choices]
DEFAULT_PAGE_SIZE = 24
MAX_PAGE_SIZE = 100


def _getlist(params, name):
    if hasattr(params, "getlist"):
        return params.getlist(name)
    value = params.get(name, [])
    return value if isinstance(value, list) else [value]


def _minimum_price(params):
    raw_value = params.get("min_price", "")
    return raw_value if raw_value else None


def _maximum_price(params):
    raw_value = params.get("max_price", "")
    return raw_value if raw_value else None


def _available_only(params):
    return params.get("available", "") in {"1", "true", "on", "yes"}


def list_cards(params, *, limit=None):
    queryset = _filter_and_sort_display_variants(params)
    if limit is not None:
        queryset = queryset[:limit]
    return [_variant_to_frontend_card(variant) for variant in queryset]


def get_most_expensive_card_sold_this_month():
    now = timezone.localtime()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if month_start.month == 12:
        next_month_start = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month_start = month_start.replace(month=month_start.month + 1)

    line = (
        PurchaseOrderLine.objects.filter(
            purchase_order__status=PurchaseOrder.Status.COMPLETED,
            purchase_order__created_at__gte=month_start,
            purchase_order__created_at__lt=next_month_start,
        )
        .select_related(
            "purchase_order",
            "card_variant__card__game",
            "card_variant__set",
            "card_variant__image",
        )
        .order_by("-unit_price", "-purchase_order__created_at", "-id")
        .first()
    )
    if line is None:
        return None

    card = _variant_to_frontend_card(line.card_variant)
    card.update(
        {
            "sale_price": line.unit_price,
            "sale_quantity": line.quantity,
            "sale_total": line.line_total,
            "sale_currency": line.purchase_order.currency,
            "sold_at": line.purchase_order.created_at,
        }
    )
    return card


def list_card_page(params):
    page_size = _positive_int(params.get("page_size"), DEFAULT_PAGE_SIZE)
    page_size = min(page_size, MAX_PAGE_SIZE)
    paginator = Paginator(_filter_and_sort_display_variants(params), page_size)
    page_obj = paginator.get_page(params.get("page"))

    return {
        "results": [_variant_to_frontend_card(variant) for variant in page_obj.object_list],
        "count": paginator.count,
        "page": page_obj.number,
        "page_size": page_size,
        "num_pages": paginator.num_pages,
        "has_previous": page_obj.has_previous(),
        "has_next": page_obj.has_next(),
        "previous_page_number": page_obj.previous_page_number() if page_obj.has_previous() else None,
        "next_page_number": page_obj.next_page_number() if page_obj.has_next() else None,
    }


def _filter_and_sort_display_variants(params):
    queryset = _display_variant_queryset()
    query = params.get("q", "").strip()
    game = params.get("game", "")
    set_name = params.get("set", "")
    language = params.get("language", "")
    selected_rarities = [rarity for rarity in _getlist(params, "rarity") if rarity]
    min_price = _minimum_price(params)
    max_price = _maximum_price(params)
    available_only = _available_only(params)

    if query:
        queryset = queryset.filter(card__name__icontains=query)
    if game:
        queryset = queryset.filter(card__game__name=game)
    if set_name:
        queryset = queryset.filter(set__name=set_name)
    if selected_rarities:
        queryset = queryset.filter(rarity__in=selected_rarities)
    if language:
        queryset = queryset.filter(language=language)
    if min_price is not None:
        queryset = queryset.filter(current_value__gte=min_price)
    if max_price is not None:
        queryset = queryset.filter(current_value__lte=max_price)
    if available_only:
        active_listing = MarketListing.objects.filter(
            inventory_item__card_variant=OuterRef("pk"),
            status=MarketListing.Status.ACTIVE,
            quantity_available__gt=0,
        )
        queryset = queryset.annotate(has_active_listing=Exists(active_listing)).filter(has_active_listing=True)

    sort = params.get("sort", "name")
    if sort == "value_desc":
        queryset = queryset.order_by("-current_value", "card__name", "id")
    elif sort == "value_asc":
        queryset = queryset.order_by("current_value", "card__name", "id")
    elif sort == "newest":
        queryset = queryset.order_by("-created_at", "id")
    else:
        queryset = queryset.order_by("card__name", "set__name", "collector_number", "id")

    return queryset


def get_card(card_id):
    card = (
        Card.objects.select_related("game")
        .prefetch_related("variants__set", "variants__image")
        .filter(pk=card_id)
        .first()
    )
    if card is None:
        return None

    variant = _first_display_variant(card)
    if variant is None:
        return {
            "id": card.id,
            "variant_id": None,
            "name": card.name,
            "game": card.game.name,
            "set_name": "",
            "rarity": "",
            "language": "",
            "edition": "",
            "current_value": card.current_value if hasattr(card, "current_value") else 0,
            "image_url": "",
        }

    return _variant_to_frontend_card(variant)


def get_card_facets():
    variants = CardVariant.objects.select_related("card__game", "set")
    return {
        "games": list(CardGame.objects.order_by("name").values_list("name", flat=True)),
        "sets": list(CardSet.objects.order_by("name").values_list("name", flat=True)),
        "rarities": list(variants.order_by("rarity").values_list("rarity", flat=True).distinct()),
        "languages": list(variants.order_by("language").values_list("language", flat=True).distinct()),
        "total_cards": Card.objects.count(),
    }


def list_active_listings_for_card(card_id):
    listings = (
        MarketListing.objects.filter(
            inventory_item__card_variant__card_id=card_id,
            status=MarketListing.Status.ACTIVE,
            quantity_available__gt=0,
        )
        .select_related(
            "seller",
            "inventory_item__card_variant__card__game",
            "inventory_item__card_variant__set",
            "inventory_item__card_variant__image",
        )
        .order_by("unit_price", "id")
    )
    return [_listing_to_card_listing(listing) for listing in listings]


def list_similar_cards(card):
    if not card.get("game") or not card.get("rarity"):
        return []

    variants = (
        _display_variant_queryset()
        .filter(card__game__name=card["game"], rarity=card["rarity"])
        .exclude(card_id=card["id"])
        .order_by("card__name", "id")[:6]
    )
    return [_variant_to_frontend_card(variant) for variant in variants]


def build_price_history(card):
    variant_id = card.get("variant_id")
    if not variant_id:
        return []

    snapshots = PriceSnapshot.objects.filter(card_variant_id=variant_id).order_by("-captured_at", "-id")
    return [
        {
            "date": snapshot.captured_at.date(),
            "price": snapshot.price,
            "source": snapshot.source_name,
        }
        for snapshot in snapshots
    ]


def _display_variant_queryset():
    return CardVariant.objects.select_related("card__game", "set", "image")


def _positive_int(raw_value, default):
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def _first_display_variant(card):
    return sorted(
        card.variants.all(),
        key=lambda variant: (variant.set.name, variant.collector_number, variant.id),
    )[0] if card.variants.exists() else None


def _variant_to_frontend_card(variant):
    try:
        image = variant.image
    except CardVariant.image.RelatedObjectDoesNotExist:
        image = None
    return {
        "id": variant.card_id,
        "variant_id": variant.id,
        "name": variant.card.name,
        "game": variant.card.game.name,
        "set_name": variant.set.name,
        "rarity": variant.rarity,
        "finish": variant.finish,
        "language": variant.language,
        "edition": variant.edition_label,
        "current_value": variant.current_value,
        "image_url": image.image_url if image else "",
    }


def _listing_to_card_listing(listing):
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
