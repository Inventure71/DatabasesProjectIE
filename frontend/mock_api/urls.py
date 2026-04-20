from django.urls import path

from frontend.mock_api import views

urlpatterns = [
    path("catalog/cards/", views.mock_cards, name="mock-catalog-cards"),
    path("marketplace/listings/", views.mock_listings, name="mock-marketplace-listings"),
]
