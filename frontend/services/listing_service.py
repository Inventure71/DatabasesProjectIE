from .catalog_service import RARITIES, _getlist, _maximum_price, _minimum_price
from .mock_data import FAKE_LISTINGS


def list_listings(params):
    listings = list(FAKE_LISTINGS)
    query = params.get("q", "").strip().lower()
    game = params.get("game", "")
    selected_rarities = [rarity for rarity in _getlist(params, "rarity") if rarity]
    min_price = _minimum_price(params)
    max_price = _maximum_price(params)

    if query:
        listings = [listing for listing in listings if query in listing["card"]["name"].lower()]
    if game:
        listings = [listing for listing in listings if listing["card"]["game"] == game]
    if selected_rarities:
        listings = [listing for listing in listings if listing["card"]["rarity"] in selected_rarities]
    if min_price is not None:
        listings = [listing for listing in listings if listing["price_per_unit"] >= min_price]
    if max_price is not None:
        listings = [listing for listing in listings if listing["price_per_unit"] <= max_price]

    sort = params.get("sort", "newest")
    if sort == "price_asc":
        return sorted(listings, key=lambda listing: listing["price_per_unit"])
    if sort == "price_desc":
        return sorted(listings, key=lambda listing: listing["price_per_unit"], reverse=True)
    if sort == "name":
        return sorted(listings, key=lambda listing: listing["card"]["name"])
    return sorted(listings, key=lambda listing: listing["id"], reverse=True)


def get_listing(listing_id):
    return next((listing for listing in FAKE_LISTINGS if listing["id"] == listing_id), None)


def get_listing_facets():
    return {
        "games": sorted({listing["card"]["game"] for listing in FAKE_LISTINGS}),
        "rarities": RARITIES,
        "total_listings": len(FAKE_LISTINGS),
    }
