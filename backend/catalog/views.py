from rest_framework.pagination import PageNumberPagination
from rest_framework.generics import ListAPIView, RetrieveAPIView

from catalog.models import Card, CardSet, CardVariant
from catalog.serializers import (
    CardDetailSerializer,
    CardListSerializer,
    CardSetSerializer,
    CardVariantDetailSerializer,
)


class CatalogPageNumberPagination(PageNumberPagination):
    page_size = 24
    page_size_query_param = "page_size"
    max_page_size = 100


class CardListView(ListAPIView):
    serializer_class = CardListSerializer
    pagination_class = CatalogPageNumberPagination

    def get_queryset(self):
        queryset = Card.objects.select_related("game").order_by("name")
        name = self.request.query_params.get("name")
        game = self.request.query_params.get("game")
        set_code = self.request.query_params.get("set")
        rarity = self.request.query_params.get("rarity")

        if name:
            queryset = queryset.filter(name__icontains=name)
        if game:
            queryset = queryset.filter(game__slug=game)
        if set_code:
            queryset = queryset.filter(variants__set__code=set_code)
        if rarity:
            queryset = queryset.filter(variants__rarity=rarity)

        return queryset.distinct()


class CardDetailView(RetrieveAPIView):
    serializer_class = CardDetailSerializer
    queryset = (
        Card.objects.select_related("game")
        .prefetch_related("variants__set__game")
        .order_by("name")
    )


class CardVariantDetailView(RetrieveAPIView):
    serializer_class = CardVariantDetailSerializer
    queryset = CardVariant.objects.select_related("card__game", "set__game", "image")


class CardSetListView(ListAPIView):
    serializer_class = CardSetSerializer
    queryset = CardSet.objects.select_related("game").order_by("game__name", "name")
