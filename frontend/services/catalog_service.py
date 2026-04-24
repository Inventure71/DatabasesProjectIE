from decimal import Decimal

from django.contrib.postgres.search import TrigramSimilarity
from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, Exists, ExpressionWrapper, F, OuterRef, Sum, Value
from django.db.models.functions import Coalesce, Greatest
from django.utils import timezone

from catalog.models import Card, CardGame, CardSet, CardVariant
from marketplace.models import MarketListing, PurchaseOrder, PurchaseOrderLine
from pricing.models import PriceSnapshot

RARITIES = [choice[0] for choice in CardVariant.Rarity.choices]
DEFAULT_PAGE_SIZE = 24
MAX_PAGE_SIZE = 100
SEARCH_SIMILARITY_THRESHOLD = 0.1
ZERO_MONEY = Value(Decimal("0"), output_field=DecimalField(max_digits=12, decimal_places=2))


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


def _valid_selected_set_name(*, game_name, set_name):
    if not game_name or not set_name:
        return ""
    if CardSet.objects.filter(game__name=game_name, name=set_name).exists():
        return set_name
    return ""


def normalize_catalog_filter_params(params):
    normalized = params.copy()
    game = normalized.get("game", "")
    set_name = normalized.get("set", "")
    if set_name and _valid_selected_set_name(game_name=game, set_name=set_name) != set_name:
        normalized.pop("set", None)
    return normalized


def _current_month_bounds():
    now = timezone.localtime()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if month_start.month == 12:
        next_month_start = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month_start = month_start.replace(month=month_start.month + 1)
    return month_start, next_month_start


def list_cards(params, *, limit=None):
    queryset = _filter_and_sort_display_variants(params)
    if limit is not None:
        queryset = queryset[:limit]
    return [_variant_to_frontend_card(variant) for variant in queryset]


def list_catalog_set_summaries(params):
    queryset = _filter_and_sort_display_variants(params).order_by()
    rows = list(
        queryset.values("set_id", "set__name", "card__game__name")
        .annotate(
            record_count=Count("id"),
            unit_count=Count("id"),
            total_value=Coalesce(Sum("current_value"), ZERO_MONEY),
        )
        .order_by("card__game__name", "set__name")
    )
    cover_cards = _cover_cards_by_set(params, [row["set_id"] for row in rows])

    return [
        {
            "set_name": row["set__name"],
            "game": row["card__game__name"],
            "cover_card": cover_cards.get(row["set_id"]),
            "record_count": row["record_count"],
            "unit_count": row["unit_count"],
            "total_value": row["total_value"],
            "query": _query_with(params, view="card", set=row["set__name"], page=None),
            "is_active": params.get("set", "") == row["set__name"],
        }
        for row in rows
    ]


def list_catalog_game_summaries(params):
    queryset = _filter_and_sort_display_variants(params).order_by()
    rows = list(
        queryset.values("card__game__name")
        .annotate(
            set_count=Count("set_id", distinct=True),
            record_count=Count("id"),
            unit_count=Count("id"),
            total_value=Coalesce(Sum("current_value"), ZERO_MONEY),
        )
        .order_by("card__game__name")
    )
    cover_cards = _cover_cards_by_game(params, [row["card__game__name"] for row in rows])

    return [
        {
            "game": row["card__game__name"],
            "cover_card": cover_cards.get(row["card__game__name"]),
            "set_count": row["set_count"],
            "record_count": row["record_count"],
            "unit_count": row["unit_count"],
            "total_value": row["total_value"],
            "query": _query_with(params, view="set", game=row["card__game__name"], set=None, page=None),
            "is_active": params.get("game", "") == row["card__game__name"],
        }
        for row in rows
    ]


def list_top_sold_cards_this_month(*, limit=6):
    month_start, next_month_start = _current_month_bounds()
    sale_total = ExpressionWrapper(
        F("quantity") * F("unit_price"),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )

    sold_rows = list(
        PurchaseOrderLine.objects.filter(
            purchase_order__status=PurchaseOrder.Status.COMPLETED,
            purchase_order__created_at__gte=month_start,
            purchase_order__created_at__lt=next_month_start,
        )
        .values("card_variant_id")
        .annotate(
            sold_quantity=Sum("quantity"),
            sales_total=Sum(sale_total),
        )
        .order_by("-sold_quantity", "-sales_total", "card_variant_id")[:limit]
    )

    variant_ids = [row["card_variant_id"] for row in sold_rows]
    if len(variant_ids) < limit:
        fallback_limit = limit - len(variant_ids)
        fallback_queryset = _display_variant_queryset()
        if variant_ids:
            fallback_queryset = fallback_queryset.exclude(pk__in=variant_ids)
        fallback_ids = list(
            fallback_queryset.order_by("-current_value", "card__name", "id")
            .values_list("id", flat=True)[:fallback_limit]
        )
        variant_ids.extend(fallback_ids)

    variants_by_id = {
        variant.id: variant
        for variant in _display_variant_queryset().filter(pk__in=variant_ids)
    }

    return [
        _variant_to_frontend_card(variants_by_id[variant_id])
        for variant_id in variant_ids
        if variant_id in variants_by_id
    ]


def get_most_expensive_card_sold_this_month():
    month_start, next_month_start = _current_month_bounds()

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
    set_name = _valid_selected_set_name(game_name=game, set_name=params.get("set", ""))
    language = params.get("language", "")
    selected_rarities = [rarity for rarity in _getlist(params, "rarity") if rarity]
    min_price = _minimum_price(params)
    max_price = _maximum_price(params)
    available_only = _available_only(params)

    if query:
        queryset = queryset.annotate(search_rank=_catalog_search_rank(query)).filter(
            search_rank__gt=SEARCH_SIMILARITY_THRESHOLD
        )
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
        if query:
            queryset = queryset.order_by("-search_rank", "card__name", "set__name", "collector_number", "id")
        else:
            queryset = queryset.order_by("card__name", "set__name", "collector_number", "id")

    return queryset


def get_card(card_id):
    card = Card.objects.select_related("game").filter(pk=card_id).first()
    if card is None:
        return None

    variant = (
        _display_variant_queryset()
        .filter(card_id=card_id)
        .order_by("set__name", "collector_number", "id")
        .first()
    )
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


def get_card_variant(variant_id):
    variant = _display_variant_queryset().filter(pk=variant_id).first()
    if variant is None:
        return None
    return _variant_to_frontend_card(variant)


def card_variant_belongs_to_card(*, card_id, variant_id):
    return CardVariant.objects.filter(pk=variant_id, card_id=card_id).exists()


def get_card_facets(params=None):
    params = params or {}
    selected_game = params.get("game", "")
    variants = CardVariant.objects.select_related("card__game", "set")
    sets = CardSet.objects.none()
    if selected_game:
        sets = CardSet.objects.filter(game__name=selected_game).order_by("name")

    return {
        "games": list(CardGame.objects.order_by("name").values_list("name", flat=True)),
        "sets": list(sets.values_list("name", flat=True)),
        "rarities": list(variants.order_by("rarity").values_list("rarity", flat=True).distinct()),
        "languages": list(variants.order_by("language").values_list("language", flat=True).distinct()),
        "total_cards": Card.objects.count(),
    }


def list_active_listings_for_variant(variant_id):
    listings = (
        MarketListing.objects.filter(
            inventory_item__card_variant_id=variant_id,
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


def build_price_history(card, *, limit=24):
    variant_id = card.get("variant_id")
    if not variant_id:
        return []

    snapshots = PriceSnapshot.objects.filter(card_variant_id=variant_id).order_by("-captured_at", "-id")[:limit]
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


def _cover_cards_by_set(params, set_ids):
    covers = {}
    if not set_ids:
        return covers
    variants = (
        _filter_and_sort_display_variants(params)
        .filter(set_id__in=set_ids)
        .order_by("set_id", "card__name", "collector_number", "id")
        .distinct("set_id")
    )
    for variant in variants:
        covers.setdefault(variant.set_id, _variant_to_frontend_card(variant))
    return covers


def _cover_cards_by_game(params, games):
    covers = {}
    if not games:
        return covers
    variants = (
        _filter_and_sort_display_variants(params)
        .filter(card__game__name__in=games)
        .order_by("card__game__name", "card__name", "set__name", "collector_number", "id")
        .distinct("card__game__name")
    )
    for variant in variants:
        covers.setdefault(variant.card.game.name, _variant_to_frontend_card(variant))
    return covers


def _catalog_search_rank(query):
    return Greatest(
        TrigramSimilarity("card__name", query),
        TrigramSimilarity("card__card_type", query),
        TrigramSimilarity("card__subtype", query),
        TrigramSimilarity("card__artist_name", query),
        TrigramSimilarity("collector_number", query),
        TrigramSimilarity("edition_label", query),
    )


def _query_with(params, **updates):
    query = params.copy()
    for key, value in updates.items():
        if value in (None, ""):
            query.pop(key, None)
        else:
            query[key] = value
    return query.urlencode()
