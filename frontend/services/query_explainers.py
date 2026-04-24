QUERY_EXPLAINERS = {
    "monthly_showcase": {
        "id": "query-help-monthly-showcase",
        "title": "Monthly top sale query",
        "summary": "Asks for the highest unit-price completed sale from the current calendar month.",
        "path": "frontend.services.catalog_service.get_most_expensive_card_sold_this_month",
        "tables": "PurchaseOrderLine, PurchaseOrder, CardVariant, Card, CardGame, CardSet, CardImage",
        "steps": [
            "Define the month window with a start timestamp and an exclusive next-month timestamp.",
            "Ask for purchase order lines whose orders are completed inside that month window.",
            "Ask for the related order, card, game, set, and image rows in the same query path.",
            "Order matching rows by highest unit price, newest purchase time, and newest line id.",
            "Read the first matching row as the monthly top sale.",
        ],
        "orm": (
            "PurchaseOrderLine.objects.filter(\n"
            "    purchase_order__status=COMPLETED,\n"
            "    purchase_order__created_at__gte=month_start,\n"
            "    purchase_order__created_at__lt=next_month_start,\n"
            ").select_related(...).order_by(\n"
            "    '-unit_price', '-purchase_order__created_at', '-id'\n"
            ").first()"
        ),
    },
    "latest_listings": {
        "id": "query-help-latest-listings",
        "title": "Latest listings query",
        "summary": "Asks for the newest active marketplace listings that still have stock available.",
        "path": "frontend.services.listing_service.list_listings",
        "tables": "MarketListing, InventoryItem, CardVariant, Card, CardGame, CardSet, CardImage, User",
        "steps": [
            "Ask for MarketListing rows with ACTIVE status and quantity_available greater than zero.",
            "Ask for seller, inventory item, card variant, card, game, set, and image rows through the listing relationship.",
            "Apply any search or filter parameters supplied by the browsing surface.",
            "Order listings by newest created_at value, then id for stable results.",
            "Limit the answer to the six rows displayed on the home page.",
        ],
        "orm": (
            "MarketListing.objects.filter(\n"
            "    status=ACTIVE,\n"
            "    quantity_available__gt=0,\n"
            ").select_related(...).order_by('-created_at', 'id')[:6]"
        ),
    },
    "featured_cards": {
        "id": "query-help-featured-cards",
        "title": "Featured cards query",
        "summary": "Asks for this month's top sold variants and any fallback catalog variants needed for the display.",
        "path": "frontend.services.catalog_service.list_top_sold_cards_this_month",
        "tables": "PurchaseOrderLine, PurchaseOrder, CardVariant, Card, CardGame, CardSet, CardImage",
        "steps": [
            "Ask for purchase order lines whose orders are completed inside the current calendar month.",
            "Group the matching rows by card_variant_id.",
            "Ask SQL to calculate total quantity sold and total sales value for each variant group.",
            "Order variant groups by most units sold, highest sales value, and card_variant_id.",
            "If the sales answer has fewer than six variants, ask CardVariant for the remaining display slots.",
            "Filter fallback variants so already-selected sale variants are not repeated.",
            "Read the selected CardVariant rows in display priority order.",
        ],
        "orm": (
            "PurchaseOrderLine.objects.filter(...).values('card_variant_id')\n"
            "    .annotate(sold_quantity=Sum('quantity'), sales_total=Sum(quantity * unit_price))\n"
            "    .order_by('-sold_quantity', '-sales_total', 'card_variant_id')[:6]\n"
            "CardVariant.objects.exclude(pk__in=sold_ids)\n"
            "    .order_by('-current_value', 'card__name', 'id')[:missing_slots]"
        ),
    },
    "catalog_results": {
        "id": "query-help-catalog-results",
        "title": "Catalog browser query",
        "summary": "Asks for filtered card variants, paginated card rows, and grouped book/shelf summaries.",
        "path": "frontend.services.catalog_service.list_card_page + list_catalog_set_summaries",
        "tables": "CardVariant, Card, CardGame, CardSet, CardImage, MarketListing",
        "steps": [
            "Ask from CardVariant rows because each result represents an exact printing.",
            "Ask for related Card, CardGame, CardSet, and CardImage rows through the variant relationship.",
            "Apply sidebar filters in SQL: trigram identity search plus game, set, rarity, language, and value range.",
            "When Only available is checked, ask EXISTS whether the same variant has an active listing with available quantity.",
            "For card view, apply the selected sort order and ask for only the current page with LIMIT and OFFSET.",
            "For book and shelf views, ask GROUP BY queries to calculate Count and Sum totals per set or game.",
            "Ask PostgreSQL DISTINCT ON for one ordered cover card per book or shelf.",
        ],
        "orm": (
            "CardVariant.objects.select_related('card__game', 'set', 'image')\n"
            "    .annotate(search_rank=Greatest(TrigramSimilarity(...)))\n"
            "    .filter(search_rank__gt=0.1)\n"
            "    .annotate(has_active_listing=Exists(MarketListing.objects.filter(...)))\n"
            "    .order_by(...)\n"
            "    # Paginator applies LIMIT/OFFSET for card view\n"
            "queryset.values('set_id', 'set__name').annotate(Count('id'), Sum('current_value'))\n"
            "queryset.order_by('set_id', ...).distinct('set_id')"
        ),
    },
    "active_listings": {
        "id": "query-help-active-listings",
        "title": "Card active listings query",
        "summary": "Asks for buyable listings for the exact card variant opened on the detail page.",
        "path": "frontend.services.catalog_service.list_active_listings_for_variant",
        "tables": "MarketListing, InventoryItem, CardVariant, Card, CardGame, CardSet, CardImage, User",
        "steps": [
            "Use the selected card_variant_id from the detail URL as the lookup value.",
            "Ask for listings whose InventoryItem points to that variant.",
            "Filter to ACTIVE listings with quantity_available greater than zero.",
            "Ask for seller and card metadata rows through the listing relationship.",
            "Order by lowest unit price first, then id for stable buy options.",
        ],
        "orm": (
            "MarketListing.objects.filter(\n"
            "    inventory_item__card_variant_id=variant_id,\n"
            "    status=ACTIVE,\n"
            "    quantity_available__gt=0,\n"
            ").select_related(...).order_by('unit_price', 'id')"
        ),
    },
    "your_copies": {
        "id": "query-help-your-copies",
        "title": "Your copies query",
        "summary": "Asks for the signed-in user's owned inventory rows for this exact card variant.",
        "path": "frontend.services.backend_api.list_my_inventory_for_variant",
        "tables": "InventoryItem, MarketListing, CardVariant, Card, CardGame, CardSet, CardImage",
        "steps": [
            "Ask for InventoryItem rows owned by request.user.",
            "Filter to the current card_variant_id from the detail page.",
            "Filter to rows with quantity greater than zero.",
            "Ask for card metadata rows through the inventory relationship.",
            "Ask for active listing rows linked to those inventory rows so listed quantity is available with the answer.",
        ],
        "orm": (
            "InventoryItem.objects.filter(owner=user, quantity__gt=0, card_variant_id=variant_id)\n"
            "    .select_related('card_variant__card__game', 'card_variant__set', 'card_variant__image')\n"
            "    .prefetch_related(active_listing_prefetch)"
        ),
    },
    "price_history": {
        "id": "query-help-price-history",
        "title": "Price history query",
        "summary": "Asks for the newest stored price snapshots for the exact card variant.",
        "path": "frontend.services.catalog_service.build_price_history",
        "tables": "PriceSnapshot, CardVariant",
        "steps": [
            "Use the current card variant id from the detail card data.",
            "Ask for PriceSnapshot rows with that card_variant_id.",
            "Order snapshots by newest captured_at value, then newest id for stable results.",
            "Limit the answer to the 24 newest snapshots.",
            "Read date, price, and source name from the returned rows.",
        ],
        "orm": (
            "PriceSnapshot.objects.filter(card_variant_id=variant_id)\n"
            "    .order_by('-captured_at', '-id')[:24]"
        ),
    },
    "similar_cards": {
        "id": "query-help-similar-cards",
        "title": "Similar cards query",
        "summary": "Asks for nearby catalog variants using simple database metadata.",
        "path": "frontend.services.catalog_service.list_similar_cards",
        "tables": "CardVariant, Card, CardGame, CardSet, CardImage",
        "steps": [
            "Use the opened card's game and rarity as the similarity criteria.",
            "Ask for CardVariant rows with the same game and rarity.",
            "Filter out rows that belong to the currently opened Card id.",
            "Ask for related card, game, set, and image data through the variant relationship.",
            "Order by card name and id, then limit the answer to six cards.",
        ],
        "orm": (
            "CardVariant.objects.select_related(...)\n"
            "    .filter(card__game__name=card['game'], rarity=card['rarity'])\n"
            "    .exclude(card_id=card['id'])\n"
            "    .order_by('card__name', 'id')[:6]"
        ),
    },
    "collection_summary": {
        "id": "query-help-collection-summary",
        "title": "Collection summary query",
        "summary": "Asks SQL to compute the signed-in user's owned, available, and reserved inventory totals.",
        "path": "frontend.services.backend_api.get_inventory_summary",
        "tables": "InventoryItem",
        "steps": [
            "Ask for InventoryItem rows owned by request.user with quantity greater than zero.",
            "Ask the database to SUM owned quantity.",
            "Ask the database to SUM reserved_quantity.",
            "Ask the database to calculate available quantity as SUM(quantity - reserved_quantity).",
            "Ask pricing services for estimated collection value through its own owner-scoped aggregate query.",
        ],
        "orm": (
            "InventoryItem.objects.filter(owner=user, quantity__gt=0).aggregate(\n"
            "    total_quantity=Sum('quantity'),\n"
            "    available_quantity=Sum(F('quantity') - F('reserved_quantity')),\n"
            "    reserved_quantity=Sum('reserved_quantity'),\n"
            ")"
        ),
    },
    "collection_browser": {
        "id": "query-help-collection-browser",
        "title": "Owned inventory browser query",
        "summary": "Asks for the signed-in user's owned inventory as cards, set books, or shelves.",
        "path": "frontend.services.backend_api.list_my_inventory_page + list_collection_set_summaries",
        "tables": "InventoryItem, MarketListing, CardVariant, Card, CardGame, CardSet, CardImage",
        "steps": [
            "Ask for InventoryItem rows owned by request.user with quantity greater than zero.",
            "Apply browser filters in SQL: PostgreSQL trigram similarity search, game, set, rarity, language, value range, and listed-only state.",
            "For listed-only filtering, ask EXISTS whether each inventory item has an active MarketListing row.",
            "For card view, ask for only the current inventory page with LIMIT 12 and OFFSET.",
            "For set books and game shelves, ask GROUP BY queries to calculate Count, Sum(quantity), and Sum(quantity * current_value).",
            "Ask PostgreSQL DISTINCT ON for one ordered cover card per book or shelf.",
            "Ask for active listing rows only for the visible card or cover rows so listed quantities are available with the answer.",
        ],
        "orm": (
            "InventoryItem.objects.filter(owner=user, quantity__gt=0).filter(...)\n"
            "    .annotate(search_rank=Greatest(TrigramSimilarity(...)))\n"
            "    .annotate(has_active_listing=Exists(MarketListing.objects.filter(...)))\n"
            "    # Paginator applies LIMIT 12/OFFSET for card view\n"
            "queryset.values('card_variant__set_id').annotate(Count('id'), Sum('quantity'))\n"
            "queryset.order_by('card_variant__set_id', ...).distinct('card_variant__set_id')"
        ),
    },
    "listing_detail": {
        "id": "query-help-listing-detail",
        "title": "Listing detail query",
        "summary": "Asks for one buyable listing and its related card data.",
        "path": "frontend.services.listing_service.get_listing",
        "tables": "MarketListing, InventoryItem, CardVariant, Card, CardGame, CardSet, CardImage, User",
        "steps": [
            "Ask for listings with ACTIVE status and quantity_available greater than zero.",
            "Filter by the listing id from the URL.",
            "Return no row when the listing is inactive, paused, cancelled, sold out, or unavailable.",
            "Ask for seller and card metadata rows through the listing relationship.",
            "Read the matching listing row for the detail template.",
        ],
        "orm": (
            "MarketListing.objects.filter(status=ACTIVE, quantity_available__gt=0)\n"
            "    .select_related(...)\n"
            "    .filter(pk=listing_id)\n"
            "    .first()"
        ),
    },
}


def get_query_explainers(keys):
    return {key: QUERY_EXPLAINERS[key] for key in keys}
