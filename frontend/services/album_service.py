from decimal import Decimal, InvalidOperation

from django.core.paginator import Paginator


DEFAULT_ALBUM_PAGE_SIZE = 12
CARD_VIEW = "card"
SET_VIEW = "set"
SHELF_VIEW = "shelf"
VALID_BROWSER_VIEWS = {CARD_VIEW, SET_VIEW, SHELF_VIEW}


def resolve_browser_view(params, default_view=CARD_VIEW):
    requested_view = params.get("view", default_view)
    if requested_view in VALID_BROWSER_VIEWS:
        return requested_view
    return default_view


def build_record_browser(
    records,
    params,
    *,
    mode,
    default_view=CARD_VIEW,
    page_size=DEFAULT_ALBUM_PAGE_SIZE,
    external_pagination=None,
):
    view = resolve_browser_view(params, default_view)
    records = list(records)
    if mode in {"collection", "my_listings"}:
        records = _filter_records_by_catalog_params(records, params)

    return {
        "mode": mode,
        "view": view,
        "view_options": _view_options(params, view),
        "count": external_pagination["count"] if external_pagination else len(records),
        "page": _build_page(records, params, page_size, external_pagination=external_pagination),
        "books": _build_browser_books(records, params),
        "shelves": _build_game_shelves(records, params),
    }


def build_collection_album(inventory_items, params, *, page_size=DEFAULT_ALBUM_PAGE_SIZE):
    return _build_album(
        records=inventory_items,
        params=params,
        page_size=page_size,
        mode="collection",
        title="Collection Book",
        availability_options=[
            {"value": "", "label": "All owned cards"},
            {"value": "available", "label": "Available to list"},
            {"value": "reserved", "label": "Reserved in listings"},
        ],
    )


def build_listing_album(active_listings, params, *, page_size=DEFAULT_ALBUM_PAGE_SIZE):
    return _build_album(
        records=active_listings,
        params=params,
        page_size=page_size,
        mode="listings",
        title="Listing Book",
        availability_options=[],
    )


def _build_album(*, records, params, page_size, mode, title, availability_options):
    books = _build_set_books(records, params)
    selected_set = params.get("set") or (books[0]["set_name"] if books else "")
    query = params.get("q", "").strip()
    selected_rarity = params.get("rarity", "")
    selected_availability = params.get("availability", "")
    filtered_records = _filter_records(
        records,
        selected_set=selected_set,
        query=query,
        selected_rarity=selected_rarity,
        selected_availability=selected_availability,
        mode=mode,
    )
    paginator = Paginator(filtered_records, page_size)
    page_obj = paginator.get_page(params.get("page"))

    for book in books:
        book["is_active"] = book["set_name"] == selected_set

    return {
        "mode": mode,
        "title": title,
        "books": books,
        "selected_set": selected_set,
        "filters": {
            "q": query,
            "rarity": selected_rarity,
            "availability": selected_availability,
        },
        "rarities": _rarities_for_set(records, selected_set),
        "availability_options": availability_options,
        "page": {
            "items": list(page_obj.object_list),
            "number": page_obj.number,
            "num_pages": page_obj.paginator.num_pages,
            "count": page_obj.paginator.count,
            "has_previous": page_obj.has_previous(),
            "has_next": page_obj.has_next(),
            "previous_query": _query_with(params, page=page_obj.previous_page_number())
            if page_obj.has_previous()
            else "",
            "next_query": _query_with(params, page=page_obj.next_page_number()) if page_obj.has_next() else "",
        },
    }


def _build_set_books(records, params):
    sets = {}
    for record in records:
        card = record["card"]
        set_name = card["set_name"]
        if set_name not in sets:
            sets[set_name] = {
                "set_name": set_name,
                "cover_card": card,
                "record_count": 0,
                "unit_count": 0,
                "total_value": Decimal("0"),
                "query": _query_with(params, set=set_name, page=None),
                "is_active": False,
            }

        book = sets[set_name]
        book["record_count"] += 1
        quantity = _record_quantity(record)
        book["unit_count"] += quantity
        book["total_value"] += _record_value(record, quantity)

    return sorted(sets.values(), key=lambda book: book["set_name"])


def _filter_records(records, *, selected_set, query, selected_rarity, selected_availability, mode):
    filtered = []
    normalized_query = query.lower()
    for record in records:
        card = record["card"]
        if selected_set and card["set_name"] != selected_set:
            continue
        if normalized_query and normalized_query not in card["name"].lower():
            continue
        if selected_rarity and card["rarity"] != selected_rarity:
            continue
        if mode == "collection":
            if selected_availability == "available" and record["available_quantity"] <= 0:
                continue
            if selected_availability == "reserved" and record["reserved_quantity"] <= 0:
                continue
        filtered.append(record)
    return filtered


def _rarities_for_set(records, selected_set):
    rarities = {
        record["card"]["rarity"]
        for record in records
        if not selected_set or record["card"]["set_name"] == selected_set
    }
    return sorted(rarity for rarity in rarities if rarity)


def _record_quantity(record):
    if "quantity_available" in record:
        return record["quantity_available"]
    if "quantity" in record:
        return record["quantity"]
    return 1


def _record_value(record, quantity):
    if "price_per_unit" in record:
        return record["price_per_unit"] * quantity
    if "estimated_value" in record:
        return record["estimated_value"]
    return _card_for_record(record)["current_value"] * quantity


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


def _view_options(params, active_view):
    return [
        {
            "value": CARD_VIEW,
            "label": "Card",
            "query": _query_with(params, view=CARD_VIEW, page=None),
            "is_active": active_view == CARD_VIEW,
        },
        {
            "value": SET_VIEW,
            "label": "Collection Book Cover",
            "query": _query_with(params, view=SET_VIEW, set=None, page=None),
            "is_active": active_view == SET_VIEW,
        },
        {
            "value": SHELF_VIEW,
            "label": "Shelf",
            "query": _query_with(params, view=SHELF_VIEW, game=None, page=None),
            "is_active": active_view == SHELF_VIEW,
        },
    ]


def _build_page(records, params, page_size, *, external_pagination=None):
    if external_pagination:
        return {
            "items": [_slot_for_record(record) for record in records],
            "number": external_pagination["page"],
            "num_pages": external_pagination["num_pages"],
            "count": external_pagination["count"],
            "has_previous": external_pagination["has_previous"],
            "has_next": external_pagination["has_next"],
            "previous_query": _query_with(params, page=external_pagination["previous_page_number"])
            if external_pagination["has_previous"]
            else "",
            "next_query": _query_with(params, page=external_pagination["next_page_number"])
            if external_pagination["has_next"]
            else "",
        }

    paginator = Paginator(records, page_size)
    page_obj = paginator.get_page(params.get("page"))
    return {
        "items": [_slot_for_record(record) for record in page_obj.object_list],
        "number": page_obj.number,
        "num_pages": page_obj.paginator.num_pages,
        "count": page_obj.paginator.count,
        "has_previous": page_obj.has_previous(),
        "has_next": page_obj.has_next(),
        "previous_query": _query_with(params, page=page_obj.previous_page_number()) if page_obj.has_previous() else "",
        "next_query": _query_with(params, page=page_obj.next_page_number()) if page_obj.has_next() else "",
    }


def _slot_for_record(record):
    return {
        "record": record,
        "card": _card_for_record(record),
    }


def _build_browser_books(records, params):
    books = {}
    selected_set = params.get("set", "")
    for record in records:
        card = _card_for_record(record)
        set_name = card["set_name"]
        if set_name not in books:
            books[set_name] = {
                "set_name": set_name,
                "game": card["game"],
                "cover_card": card,
                "record_count": 0,
                "unit_count": 0,
                "total_value": Decimal("0"),
                "query": _query_with(params, view=CARD_VIEW, set=set_name, page=None),
                "is_active": selected_set == set_name,
            }
        book = books[set_name]
        quantity = _record_quantity(record)
        book["record_count"] += 1
        book["unit_count"] += quantity
        book["total_value"] += _record_value(record, quantity)

    return sorted(books.values(), key=lambda book: (book["game"], book["set_name"]))


def _build_game_shelves(records, params):
    shelves = {}
    selected_game = params.get("game", "")
    for record in records:
        card = _card_for_record(record)
        game = card["game"]
        if game not in shelves:
            shelves[game] = {
                "game": game,
                "cover_card": card,
                "set_names": set(),
                "record_count": 0,
                "unit_count": 0,
                "total_value": Decimal("0"),
                "query": _query_with(params, view=SET_VIEW, game=game, set=None, page=None),
                "is_active": selected_game == game,
            }
        shelf = shelves[game]
        quantity = _record_quantity(record)
        shelf["set_names"].add(card["set_name"])
        shelf["record_count"] += 1
        shelf["unit_count"] += quantity
        shelf["total_value"] += _record_value(record, quantity)

    result = []
    for shelf in shelves.values():
        shelf["set_count"] = len(shelf["set_names"])
        del shelf["set_names"]
        result.append(shelf)
    return sorted(result, key=lambda shelf: shelf["game"])


def _filter_records_by_catalog_params(records, params):
    query = params.get("q", "").strip().lower()
    game = params.get("game", "")
    set_name = params.get("set", "")
    language = params.get("language", "")
    selected_rarities = [rarity for rarity in _getlist(params, "rarity") if rarity]
    min_price = _decimal_or_none(params.get("min_price", ""))
    max_price = _decimal_or_none(params.get("max_price", ""))

    filtered = []
    for record in records:
        card = _card_for_record(record)
        price = _record_unit_price(record)
        if query and query not in card["name"].lower():
            continue
        if game and card["game"] != game:
            continue
        if set_name and card["set_name"] != set_name:
            continue
        if language and card["language"] != language:
            continue
        if selected_rarities and card["rarity"] not in selected_rarities:
            continue
        if min_price is not None and price < min_price:
            continue
        if max_price is not None and price > max_price:
            continue
        filtered.append(record)
    return filtered


def _card_for_record(record):
    return record["card"] if "card" in record else record


def _record_unit_price(record):
    if "price_per_unit" in record:
        return record["price_per_unit"]
    if "card" in record:
        return record["card"]["current_value"]
    return record["current_value"]


def _decimal_or_none(raw_value):
    if raw_value in ("", None):
        return None
    try:
        return Decimal(raw_value)
    except (InvalidOperation, TypeError, ValueError):
        return None
