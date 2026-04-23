from decimal import Decimal, InvalidOperation

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from inventory.models import InventoryItem

from frontend.services.album_service import (
    CARD_VIEW,
    SET_VIEW,
    SHELF_VIEW,
    build_collection_album,
    build_record_browser,
    resolve_browser_view,
)
from frontend.services.backend_api import (
    add_inventory_item_for_user,
    buy_marketplace_listing,
    create_marketplace_listing_for_user,
    get_inventory_summary,
    get_collection_value,
    list_collection_game_summaries,
    list_collection_set_summaries,
    list_my_inventory,
    list_my_inventory_for_variant,
    list_my_inventory_page,
)
from frontend.services.catalog_service import (
    build_price_history,
    card_variant_belongs_to_card,
    get_card,
    get_card_facets,
    get_card_variant,
    get_most_expensive_card_sold_this_month,
    list_active_listings_for_variant,
    list_card_page,
    list_catalog_game_summaries,
    list_catalog_set_summaries,
    list_similar_cards,
    list_top_sold_cards_this_month,
    normalize_catalog_filter_params,
)
from frontend.services.listing_service import (
    get_listing,
    list_listings,
)
from frontend.services.query_explainers import get_query_explainers


def home(request):
    featured_cards = list_top_sold_cards_this_month(limit=6)
    monthly_top_sale = get_most_expensive_card_sold_this_month()
    showcase_card = monthly_top_sale or (featured_cards[0] if featured_cards else None)
    return render(
        request,
        "home.html",
        {
            "featured_cards": featured_cards,
            "showcase_card": showcase_card,
            "showcase_is_sale": monthly_top_sale is not None,
            "latest_listings": list_listings({}, limit=6),
            "query_explainers": get_query_explainers(
                [
                    "monthly_showcase",
                    "latest_listings",
                    "featured_cards",
                ]
            ),
        },
    )


def catalog(request):
    filter_params = normalize_catalog_filter_params(request.GET)
    facets = get_card_facets(filter_params)
    card_page = list_card_page(filter_params)
    browser_view = resolve_browser_view(filter_params, CARD_VIEW)
    catalog_books = list_catalog_set_summaries(filter_params) if browser_view == SET_VIEW else []
    catalog_shelves = list_catalog_game_summaries(filter_params) if browser_view == SHELF_VIEW else []
    browser_records = card_page["results"] if browser_view == CARD_VIEW else []
    browser_count = card_page["count"]
    if browser_view == SET_VIEW:
        browser_count = sum(book["record_count"] for book in catalog_books)
    elif browser_view == SHELF_VIEW:
        browser_count = sum(shelf["record_count"] for shelf in catalog_shelves)
    browser = build_record_browser(
        browser_records,
        filter_params,
        mode="catalog",
        default_view=CARD_VIEW,
        external_pagination=card_page if browser_view == CARD_VIEW else None,
        books=catalog_books,
        shelves=catalog_shelves,
        total_count=browser_count,
    )
    pagination_query = filter_params.copy()
    pagination_query.pop("page", None)

    return render(
        request,
        "catalog.html",
        {
            "cards": card_page["results"],
            "result_count": card_page["count"],
            "browser": browser,
            "pagination": card_page,
            "pagination_query": pagination_query.urlencode(),
            "total_cards": facets["total_cards"],
            "games": facets["games"],
            "sets": facets["sets"],
            "rarities": facets["rarities"],
            "languages": facets["languages"],
            "selected_game": filter_params.get("game", ""),
            "selected_set": filter_params.get("set", ""),
            "selected_rarities": filter_params.getlist("rarity"),
            "selected_available": filter_params.get("available") == "1",
            "query_explainers": get_query_explainers(["catalog_results"]),
        },
    )


def card_detail(request, card_id):
    card = get_card(card_id)
    return _render_card_detail(request, card)


def card_variant_detail(request, variant_id):
    card = get_card_variant(variant_id)
    return _render_card_detail(request, card)


def _render_card_detail(request, card):
    if not card:
        return redirect("catalog")

    sell_error = None
    owned_inventory_items = []

    variant_id = card.get("variant_id")
    detail_url = reverse("card_variant_detail", kwargs={"variant_id": variant_id}) if variant_id else reverse("catalog")

    if request.user.is_authenticated and variant_id:
        owned_inventory_items = list_my_inventory_for_variant(request.user, variant_id)

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect("login")

        try:
            inventory_item_id = int(request.POST.get("inventory_item_id", ""))
            quantity = int(request.POST.get("quantity", ""))
            unit_price = Decimal(request.POST.get("unit_price", ""))
        except (TypeError, ValueError, InvalidOperation):
            sell_error = "Enter a valid quantity and price."
        else:
            valid_inventory_ids = {item["id"] for item in owned_inventory_items}
            if inventory_item_id not in valid_inventory_ids:
                sell_error = "Choose one of your copies for this card."
            else:
                try:
                    listing = create_marketplace_listing_for_user(
                        user=request.user,
                        inventory_item_id=inventory_item_id,
                        quantity=quantity,
                        unit_price=unit_price,
                    )
                except ValidationError as exc:
                    sell_error = "; ".join(exc.messages)
                else:
                    return redirect(f"{detail_url}?listed={listing['id']}")

    return render(
        request,
        "card_detail.html",
        {
            "card": card,
            "detail_url": detail_url,
            "active_listings": list_active_listings_for_variant(variant_id) if variant_id else [],
            "price_history": build_price_history(card),
            "similar_cards": list_similar_cards(card),
            "owned_inventory_items": owned_inventory_items,
            "inventory_condition_choices": InventoryItem.Condition.choices,
            "sell_error": sell_error,
            "listed_id": request.GET.get("listed"),
            "added_id": request.GET.get("added"),
            "add_error": request.GET.get("add_error"),
            "query_explainers": get_query_explainers(
                [
                    "your_copies",
                    "active_listings",
                    "price_history",
                    "similar_cards",
                ]
            ),
        },
    )


def listings(request):
    query = request.GET.copy()
    query["available"] = "1"
    query.pop("sort", None)
    return redirect(f"{reverse('catalog')}?{query.urlencode()}#browser")


@login_required(login_url="login")
@require_POST
def add_to_collection(request):
    try:
        card_id = int(request.POST.get("card_id", ""))
        card_variant_id = int(request.POST.get("card_variant_id", ""))
        quantity = int(request.POST.get("quantity", ""))
    except (TypeError, ValueError):
        return _redirect_card_add_error(request.POST.get("card_id"))

    card = get_card(card_id)
    if not card or not card_variant_belongs_to_card(card_id=card_id, variant_id=card_variant_id):
        return _redirect_card_add_error(card_id)

    try:
        item = add_inventory_item_for_user(
            user=request.user,
            card_variant_id=card_variant_id,
            condition=request.POST.get("condition", ""),
            quantity=quantity,
        )
    except ValidationError:
        return _redirect_card_add_error(card_id)

    return redirect(f"{reverse('card_variant_detail', kwargs={'variant_id': card_variant_id})}?added={item['id']}")


def _redirect_card_add_error(card_id):
    try:
        card_id = int(card_id)
    except (TypeError, ValueError):
        return redirect("catalog")
    return redirect(f"{reverse('card_detail', kwargs={'card_id': card_id})}?add_error=1")


@login_required(login_url="login")
def collection(request):
    error = None

    if request.method == "POST":
        if request.POST.get("form_action") == "add_inventory":
            try:
                card_variant_id = int(request.POST.get("card_variant_id", ""))
                quantity = int(request.POST.get("quantity", ""))
                purchase_price = _optional_decimal(request.POST.get("purchase_price", ""))
            except (TypeError, ValueError, InvalidOperation):
                error = "Enter a valid card, quantity, and purchase price."
            else:
                try:
                    item = add_inventory_item_for_user(
                        user=request.user,
                        card_variant_id=card_variant_id,
                        condition=request.POST.get("condition", ""),
                        quantity=quantity,
                        purchase_price=purchase_price,
                    )
                except ValidationError as exc:
                    error = "; ".join(exc.messages)
                else:
                    return redirect(f"{reverse('collection')}?added={item['id']}")
        else:
            try:
                inventory_item_id = int(request.POST.get("inventory_item_id", ""))
                quantity = int(request.POST.get("quantity", ""))
                unit_price = Decimal(request.POST.get("unit_price", ""))
            except (TypeError, ValueError, InvalidOperation):
                error = "Enter a valid quantity and price."
            else:
                try:
                    listing = create_marketplace_listing_for_user(
                        user=request.user,
                        inventory_item_id=inventory_item_id,
                        quantity=quantity,
                        unit_price=unit_price,
                    )
                except ValidationError as exc:
                    error = "; ".join(exc.messages)
                else:
                    return redirect(f"{reverse('collection')}?listed={listing['id']}")

    collection_value = get_collection_value(request.user)
    filter_params = normalize_catalog_filter_params(request.GET)
    facets = get_card_facets(filter_params)
    summary = get_inventory_summary(request.user)
    browser_view = resolve_browser_view(filter_params, SET_VIEW)
    collection_page = list_my_inventory_page(request.user, filter_params) if browser_view == CARD_VIEW else None
    inventory_items = collection_page["results"] if collection_page else []
    collection_books = list_collection_set_summaries(request.user, filter_params) if browser_view == SET_VIEW else []
    collection_shelves = list_collection_game_summaries(request.user, filter_params) if browser_view == SHELF_VIEW else []
    browser_count = collection_page["count"] if collection_page else 0
    if browser_view == SET_VIEW:
        browser_count = sum(book["record_count"] for book in collection_books)
    elif browser_view == SHELF_VIEW:
        browser_count = sum(shelf["record_count"] for shelf in collection_shelves)

    return render(
        request,
        "collection.html",
        {
            "inventory_items": inventory_items,
            "album": build_collection_album(inventory_items, filter_params),
            "browser": build_record_browser(
                inventory_items,
                filter_params,
                mode="collection",
                default_view=SET_VIEW,
                external_pagination=collection_page if browser_view == CARD_VIEW else None,
                books=collection_books,
                shelves=collection_shelves,
                total_count=browser_count,
            ),
            "collection_value": collection_value,
            "summary": summary,
            "games": facets["games"],
            "sets": facets["sets"],
            "rarities": facets["rarities"],
            "languages": facets["languages"],
            "selected_game": filter_params.get("game", ""),
            "selected_set": filter_params.get("set", ""),
            "selected_rarities": filter_params.getlist("rarity"),
            "error": error,
            "listed_id": request.GET.get("listed"),
            "query_explainers": get_query_explainers(
                [
                    "collection_summary",
                    "collection_browser",
                ]
            ),
        },
    )


@login_required(login_url="login")
def my_listings(request):
    return redirect(f"{reverse('collection')}?view=card&my_listings=listed#browser")


def listing_detail(request, listing_id):
    listing = get_listing(listing_id)
    if not listing:
        return redirect("listings")

    error = None

    if request.method == "POST" and request.user.is_authenticated:
        try:
            quantity = int(request.POST.get("quantity", 1))
        except ValueError:
            error = "Invalid quantity."
        else:
            if quantity < 1:
                error = "Quantity must be at least 1."
            elif quantity > listing["quantity"]:
                error = f"Only {listing['quantity']} unit(s) available."
            else:
                try:
                    buy_marketplace_listing(
                        user=request.user,
                        listing_id=listing_id,
                        quantity=quantity,
                    )
                except ValidationError as exc:
                    error = "; ".join(exc.messages)
                else:
                    return redirect("home")

    return render(
        request,
        "listing_detail.html",
        {
            "listing": listing,
            "error": error,
            "query_explainers": get_query_explainers(["listing_detail"]),
        },
    )


@require_POST
def logout_view(request):
    logout(request)
    return redirect("home")


def register_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = UserCreationForm()

    return render(request, "register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("home")
    else:
        form = AuthenticationForm()

    return render(request, "login.html", {"form": form})


def _optional_decimal(value):
    value = value.strip() if value else ""
    return Decimal(value) if value else None
