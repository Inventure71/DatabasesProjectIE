from django.urls import path

from marketplace.views import (
    BuyListingView,
    MarketListingDetailView,
    MarketListingListView,
    MyPurchaseHistoryView,
    MySalesHistoryView,
)

urlpatterns = [
    path("listings/", MarketListingListView.as_view(), name="marketplace-listing-list"),
    path("listings/<int:pk>/", MarketListingDetailView.as_view(), name="marketplace-listing-detail"),
    path("listings/<int:pk>/buy/", BuyListingView.as_view(), name="marketplace-listing-buy"),
    path("my/sales/", MySalesHistoryView.as_view(), name="marketplace-my-sales"),
    path("my/purchases/", MyPurchaseHistoryView.as_view(), name="marketplace-my-purchases"),
]
