from .mock_data import FAKE_CARDS, FAKE_LISTINGS

RARITIES = ["common", "uncommon", "rare", "ultra", "secret"]


def _getlist(params, name):
    if hasattr(params, "getlist"):
        return params.getlist(name)
    value = params.get(name, [])
    return value if isinstance(value, list) else [value]


def _minimum_price(params):
    raw_value = params.get("min_price", "")
    return float(raw_value) if raw_value else None


def _maximum_price(params):
    raw_value = params.get("max_price", "")
    return float(raw_value) if raw_value else None


def list_cards(params):
    cards = list(FAKE_CARDS)
    query = params.get("q", "").strip().lower()
    game = params.get("game", "")
    set_name = params.get("set", "")
    language = params.get("language", "")
    selected_rarities = [rarity for rarity in _getlist(params, "rarity") if rarity]
    min_price = _minimum_price(params)
    max_price = _maximum_price(params)

    if query:
        cards = [card for card in cards if query in card["name"].lower()]
    if game:
        cards = [card for card in cards if card["game"] == game]
    if set_name:
        cards = [card for card in cards if card["set_name"] == set_name]
    if selected_rarities:
        cards = [card for card in cards if card["rarity"] in selected_rarities]
    if language:
        cards = [card for card in cards if card["language"] == language]
    if min_price is not None:
        cards = [card for card in cards if card["current_value"] >= min_price]
    if max_price is not None:
        cards = [card for card in cards if card["current_value"] <= max_price]

    sort = params.get("sort", "name")
    if sort == "value_desc":
        return sorted(cards, key=lambda card: card["current_value"], reverse=True)
    if sort == "value_asc":
        return sorted(cards, key=lambda card: card["current_value"])
    if sort == "newest":
        return sorted(cards, key=lambda card: card["created_at"], reverse=True)
    return sorted(cards, key=lambda card: card["name"])


def get_card(card_id):
    return next((card for card in FAKE_CARDS if card["id"] == card_id), None)


def get_card_facets():
    return {
        "games": sorted({card["game"] for card in FAKE_CARDS}),
        "sets": sorted({card["set_name"] for card in FAKE_CARDS}),
        "rarities": RARITIES,
        "languages": sorted({card["language"] for card in FAKE_CARDS}),
        "total_cards": len(FAKE_CARDS),
    }


def list_active_listings_for_card(card_id):
    return [listing for listing in FAKE_LISTINGS if listing["card"]["id"] == card_id]


def list_similar_cards(card):
    return [
        candidate
        for candidate in FAKE_CARDS
        if candidate["game"] == card["game"]
        and candidate["rarity"] == card["rarity"]
        and candidate["id"] != card["id"]
    ][:6]


def build_price_history(card):
    return [
        {"date": "2024-04-01", "price": round(card["current_value"] * 0.80, 2), "source": "Mock market scan"},
        {"date": "2024-03-01", "price": round(card["current_value"] * 0.85, 2), "source": "Mock market scan"},
        {"date": "2024-02-01", "price": round(card["current_value"] * 0.90, 2), "source": "Mock market scan"},
        {"date": "2024-01-01", "price": round(card["current_value"] * 0.95, 2), "source": "Mock market scan"},
    ]
