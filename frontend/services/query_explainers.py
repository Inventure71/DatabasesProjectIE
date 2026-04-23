QUERY_EXPLAINERS = {
    "monthly_showcase": {
        "id": "query-help-monthly-showcase",
        "title": "Monthly top sale query",
        "summary": "Shows the highest unit-price completed sale in the current calendar month.",
        "path": "frontend.services.catalog_service.get_most_expensive_card_sold_this_month",
        "tables": "PurchaseOrderLine, PurchaseOrder, CardVariant, Card, CardGame, CardSet, CardImage",
        "steps": [
            "Compute the first instant of the current month and the first instant of next month.",
            "Filter purchase order lines to completed orders created inside that month.",
            "Join the order, card, game, set, and image rows with select_related so the template does not trigger extra per-card queries.",
            "Order by highest unit price, then newest purchase, then newest line id.",
            "Read the first row and convert its CardVariant into the frontend card shape.",
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
        "summary": "Shows the newest active marketplace listings that still have stock available.",
        "path": "frontend.services.listing_service.list_listings",
        "tables": "MarketListing, InventoryItem, CardVariant, Card, CardGame, CardSet, CardImage, User",
        "steps": [
            "Start from MarketListing rows where status is ACTIVE and quantity_available is greater than zero.",
            "Join seller, inventory item, card variant, card, game, set, and image with select_related.",
            "Apply any search/filter parameters when the same service is used from browsing pages.",
            "Sort by newest created_at first, with id as a stable tie breaker.",
            "Apply LIMIT 6 before rendering the home page so the database returns only the displayed rows.",
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
        "summary": "Ranks this month's sold card variants, then fills any empty display slots from catalog variants.",
        "path": "frontend.services.catalog_service.list_top_sold_cards_this_month",
        "tables": "PurchaseOrderLine, PurchaseOrder, CardVariant, Card, CardGame, CardSet, CardImage",
        "steps": [
            "Filter purchase order lines to completed orders in the current calendar month.",
            "Group those rows by card_variant_id.",
            "Annotate each group with total quantity sold and total sales value.",
            "Sort by most units sold, then highest sales total, then card_variant_id for stable output.",
            "If fewer than six distinct sold variants exist, query CardVariant for the missing number of fallback catalog cards.",
            "Exclude variants already selected from sales so the Featured Cards grid does not duplicate a card.",
            "Fetch the selected CardVariant rows and convert them into frontend cards in priority order.",
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
        "summary": "Searches and filters card variants, paginates cards, and groups book/shelf summaries in the database.",
        "path": "frontend.services.catalog_service.list_card_page + list_catalog_set_summaries",
        "tables": "CardVariant, Card, CardGame, CardSet, CardImage, MarketListing",
        "steps": [
            "Start from CardVariant because inventory, listings, and pricing all depend on exact printings.",
            "Join Card, CardGame, CardSet, and CardImage with select_related.",
            "Apply the sidebar filters in SQL: MySQL-safe LIKE search over identity fields, game, set, rarity, language, and value range.",
            "When Only available is checked, add an EXISTS subquery that looks for an active listing with available quantity for the same variant.",
            "For card view, apply sort order, then Paginator adds LIMIT and OFFSET so only the visible page is read.",
            "For book and shelf views, use GROUP BY with Count and Sum annotations so the database computes set/game totals.",
        ],
        "orm": (
            "CardVariant.objects.select_related('card__game', 'set', 'image')\n"
            "    .filter(Q(card__name__icontains=q) | Q(collector_number__icontains=q) | ...)\n"
            "    .annotate(has_active_listing=Exists(MarketListing.objects.filter(...)))\n"
            "    .order_by(...)\n"
            "    # Paginator applies LIMIT/OFFSET for card view\n"
            "queryset.values('set_id', 'set__name').annotate(Count('id'), Sum('current_value'))"
        ),
    },
    "active_listings": {
        "id": "query-help-active-listings",
        "title": "Card active listings query",
        "summary": "Finds buyable listings for the exact card variant opened on the detail page.",
        "path": "frontend.services.catalog_service.list_active_listings_for_variant",
        "tables": "MarketListing, InventoryItem, CardVariant, Card, CardGame, CardSet, CardImage, User",
        "steps": [
            "Use the selected card_variant_id from the detail URL.",
            "Filter listings to that variant through InventoryItem.card_variant_id.",
            "Keep only ACTIVE listings with quantity_available greater than zero.",
            "Join seller and card metadata with select_related.",
            "Sort by lowest unit price first, then id, so cheaper buy options appear first.",
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
        "summary": "Loads the signed-in user's owned inventory rows for this exact card variant.",
        "path": "frontend.services.backend_api.list_my_inventory_for_variant",
        "tables": "InventoryItem, MarketListing, CardVariant, Card, CardGame, CardSet, CardImage",
        "steps": [
            "Filter InventoryItem to owner=request.user so users can only see their own stock.",
            "Filter to the current card_variant_id from the detail page.",
            "Ignore zero-quantity inventory rows in the frontend owned-card view.",
            "Join card metadata with select_related.",
            "Prefetch active listings for each inventory row so listed quantity can be shown without N+1 queries.",
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
        "summary": "Reads the newest stored price snapshots for the exact card variant.",
        "path": "frontend.services.catalog_service.build_price_history",
        "tables": "PriceSnapshot, CardVariant",
        "steps": [
            "Read the current card variant id from the detail card data.",
            "Filter PriceSnapshot rows to that card_variant_id.",
            "Sort newest captured_at first, then newest id for stable ordering.",
            "Apply LIMIT 24 so long histories do not load every stored snapshot.",
            "Return date, price, and source name for the displayed snapshots.",
        ],
        "orm": (
            "PriceSnapshot.objects.filter(card_variant_id=variant_id)\n"
            "    .order_by('-captured_at', '-id')[:24]"
        ),
    },
    "similar_cards": {
        "id": "query-help-similar-cards",
        "title": "Similar cards query",
        "summary": "Finds nearby catalog variants using simple database metadata.",
        "path": "frontend.services.catalog_service.list_similar_cards",
        "tables": "CardVariant, Card, CardGame, CardSet, CardImage",
        "steps": [
            "Use the opened card's game and rarity as the similarity criteria.",
            "Filter CardVariant rows to the same game and rarity.",
            "Exclude the current Card id.",
            "Join card, game, set, and image data with select_related.",
            "Sort by card name and id, then limit to six cards.",
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
        "summary": "Computes the signed-in user's owned, available, and reserved inventory totals with SQL aggregates.",
        "path": "frontend.services.backend_api.get_inventory_summary",
        "tables": "InventoryItem",
        "steps": [
            "Filter InventoryItem rows to owner=request.user and quantity greater than zero.",
            "Ask the database to SUM owned quantity.",
            "Ask the database to SUM reserved_quantity.",
            "Compute available quantity as SUM(quantity - reserved_quantity).",
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
        "summary": "Shows the signed-in user's owned inventory as cards, set books, or shelves.",
        "path": "frontend.services.backend_api.list_my_inventory_page + list_collection_set_summaries",
        "tables": "InventoryItem, MarketListing, CardVariant, Card, CardGame, CardSet, CardImage",
        "steps": [
            "Start from InventoryItem rows owned by request.user with quantity greater than zero.",
            "Apply browser filters in SQL: search, game, set, rarity, language, value range, and listed-only state.",
            "For listed-only filtering, use an EXISTS subquery against active MarketListing rows for the inventory item.",
            "For card view, Paginator applies LIMIT 12/OFFSET before inventory rows are converted for templates.",
            "For set books and game shelves, GROUP BY set or game and annotate Count, Sum(quantity), and Sum(quantity * current_value).",
            "Prefetch active listings only for the visible card rows so listed quantity pills avoid N+1 queries.",
        ],
        "orm": (
            "InventoryItem.objects.filter(owner=user, quantity__gt=0).filter(...)\n"
            "    .annotate(has_active_listing=Exists(MarketListing.objects.filter(...)))\n"
            "    # Paginator applies LIMIT 12/OFFSET for card view\n"
            "queryset.values('card_variant__set_id').annotate(Count('id'), Sum('quantity'))"
        ),
    },
    "listing_detail": {
        "id": "query-help-listing-detail",
        "title": "Listing detail query",
        "summary": "Loads one buyable listing and its related card data.",
        "path": "frontend.services.listing_service.get_listing",
        "tables": "MarketListing, InventoryItem, CardVariant, Card, CardGame, CardSet, CardImage, User",
        "steps": [
            "Start from the active listing queryset shared with marketplace browsing.",
            "Filter by the listing id from the URL.",
            "Reject inactive, paused, cancelled, sold-out, or unavailable listings by returning no row.",
            "Join seller and card metadata with select_related.",
            "Convert the listing into the template's frontend listing shape.",
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
