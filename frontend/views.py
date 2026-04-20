from decimal import Decimal, InvalidOperation

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from frontend.services.album_service import (
    CARD_VIEW,
    SET_VIEW,
    build_collection_album,
    build_record_browser,
    resolve_browser_view,
)
from frontend.services.backend_api import (
    buy_marketplace_listing,
    create_marketplace_listing_for_user,
    get_collection_value,
    list_my_inventory,
)
from frontend.services.catalog_service import (
    build_price_history,
    get_card,
    get_card_facets,
    get_most_expensive_card_sold_this_month,
    list_active_listings_for_card,
    list_card_page,
    list_cards,
    list_similar_cards,
)
from frontend.services.listing_service import (
    get_listing,
    list_listings,
)


def home(request):
    featured_cards = list_cards({}, limit=6)
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
        },
    )


def catalog(request):
    facets = get_card_facets()
    card_page = list_card_page(request.GET)
    browser_view = resolve_browser_view(request.GET, CARD_VIEW)
    browser_records = card_page["results"] if browser_view == CARD_VIEW else list_cards(request.GET)
    browser = build_record_browser(
        browser_records,
        request.GET,
        mode="catalog",
        default_view=CARD_VIEW,
        external_pagination=card_page if browser_view == CARD_VIEW else None,
    )
    pagination_query = request.GET.copy()
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
            "selected_rarities": request.GET.getlist("rarity"),
            "selected_available": request.GET.get("available") == "1",
        },
    )


def card_detail(request, card_id):
    card = get_card(card_id)
    if not card:
        return redirect("catalog")

    sell_error = None
    owned_inventory_items = []

    if request.user.is_authenticated:
        owned_inventory_items = [
            item for item in list_my_inventory(request.user)
            if item["card"]["id"] == card_id
        ]

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
                    return redirect(f"{reverse('card_detail', kwargs={'card_id': card_id})}?listed={listing['id']}")

    return render(
        request,
        "card_detail.html",
        {
            "card": card,
            "active_listings": list_active_listings_for_card(card_id),
            "price_history": build_price_history(card),
            "similar_cards": list_similar_cards(card),
            "owned_inventory_items": owned_inventory_items,
            "sell_error": sell_error,
            "listed_id": request.GET.get("listed"),
        },
    )


def listings(request):
    query = request.GET.copy()
    query["available"] = "1"
    query.pop("sort", None)
    return redirect(f"{reverse('catalog')}?{query.urlencode()}#browser")


@login_required(login_url="login")
def collection(request):
    error = None

    if request.method == "POST":
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

    inventory_items = list_my_inventory(request.user)
    collection_value = get_collection_value(request.user)
    facets = get_card_facets()
    summary = {
        "total_quantity": sum(item["quantity"] for item in inventory_items),
        "available_quantity": sum(item["available_quantity"] for item in inventory_items),
        "reserved_quantity": sum(item["reserved_quantity"] for item in inventory_items),
    }

    return render(
        request,
        "collection.html",
        {
            "inventory_items": inventory_items,
            "album": build_collection_album(inventory_items, request.GET),
            "browser": build_record_browser(
                inventory_items,
                request.GET,
                mode="collection",
                default_view=SET_VIEW,
            ),
            "collection_value": collection_value,
            "summary": summary,
            "games": facets["games"],
            "sets": facets["sets"],
            "rarities": facets["rarities"],
            "languages": facets["languages"],
            "selected_rarities": request.GET.getlist("rarity"),
            "error": error,
            "listed_id": request.GET.get("listed"),
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
