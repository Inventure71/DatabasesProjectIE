from django.urls import path

from pricing.views import MyCollectionValueView, VariantPriceHistoryView

urlpatterns = [
    path(
        "variants/<int:variant_id>/history/",
        VariantPriceHistoryView.as_view(),
        name="pricing-variant-history",
    ),
    path(
        "my/collection-value/",
        MyCollectionValueView.as_view(),
        name="pricing-my-collection-value",
    ),
]
