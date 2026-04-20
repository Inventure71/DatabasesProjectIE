from django.urls import path

from catalog.views import CardDetailView, CardListView, CardSetListView, CardVariantDetailView

urlpatterns = [
    path("cards/", CardListView.as_view(), name="catalog-card-list"),
    path("cards/<int:pk>/", CardDetailView.as_view(), name="catalog-card-detail"),
    path("variants/<int:pk>/", CardVariantDetailView.as_view(), name="catalog-variant-detail"),
    path("sets/", CardSetListView.as_view(), name="catalog-set-list"),
]
