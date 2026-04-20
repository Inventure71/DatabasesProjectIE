from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from frontend.services.backend_api import buy_marketplace_listing
from frontend.services.catalog_service import (
    build_price_history,
    get_card,
    get_card_facets,
    list_active_listings_for_card,
    list_card_page,
    list_cards,
    list_similar_cards,
)
from frontend.services.listing_service import (
    get_listing,
    get_listing_facets,
    list_listings,
)


def home(request):
    return render(
        request,
        "home.html",
        {
            "featured_cards": list_cards({}, limit=6),
            "latest_listings": list_listings({}, limit=6),
        },
    )


def catalog(request):
    facets = get_card_facets()
    card_page = list_card_page(request.GET)
    pagination_query = request.GET.copy()
    pagination_query.pop("page", None)

    return render(
        request,
        "catalog.html",
        {
            "cards": card_page["results"],
            "result_count": card_page["count"],
            "pagination": card_page,
            "pagination_query": pagination_query.urlencode(),
            "total_cards": facets["total_cards"],
            "games": facets["games"],
            "sets": facets["sets"],
            "rarities": facets["rarities"],
            "languages": facets["languages"],
            "selected_rarities": request.GET.getlist("rarity"),
        },
    )


def card_detail(request, card_id):
    card = get_card(card_id)
    if not card:
        return redirect("catalog")

    return render(
        request,
        "card_detail.html",
        {
            "card": card,
            "active_listings": list_active_listings_for_card(card_id),
            "price_history": build_price_history(card),
            "similar_cards": list_similar_cards(card),
        },
    )


def listings(request):
    facets = get_listing_facets()

    return render(
        request,
        "listings.html",
        {
            "listings": list_listings(request.GET),
            "total_listings": facets["total_listings"],
            "games": facets["games"],
            "rarities": facets["rarities"],
            "selected_rarities": request.GET.getlist("rarity"),
        },
    )


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
