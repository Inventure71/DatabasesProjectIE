from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import CardVariant
from pricing.serializers import CollectionValueSerializer, PriceSnapshotSerializer
from pricing.services import estimate_collection_value, get_variant_price_history


class PriceHistoryPageNumberPagination(PageNumberPagination):
    page_size = 24
    page_size_query_param = "page_size"
    max_page_size = 100


class VariantPriceHistoryView(ListAPIView):
    serializer_class = PriceSnapshotSerializer
    permission_classes = [AllowAny]
    pagination_class = PriceHistoryPageNumberPagination

    def get_queryset(self):
        variant = get_object_or_404(CardVariant, pk=self.kwargs["variant_id"])
        return get_variant_price_history(card_variant=variant)


class MyCollectionValueView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = {
            "total_value": estimate_collection_value(owner=request.user),
            "currency": "EUR",
        }
        return Response(CollectionValueSerializer(data).data)
