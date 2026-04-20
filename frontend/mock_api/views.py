from django.http import JsonResponse

from frontend.services.catalog_service import list_cards
from frontend.services.listing_service import list_listings


def mock_cards(request):
    return JsonResponse({"results": list_cards(request.GET)})


def mock_listings(request):
    return JsonResponse({"results": list_listings(request.GET)})
