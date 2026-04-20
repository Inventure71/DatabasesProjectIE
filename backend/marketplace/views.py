from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from marketplace.models import MarketListing, PurchaseOrder, PurchaseOrderLine
from marketplace.serializers import BuyListingSerializer, MarketListingSerializer, PurchaseOrderSerializer
from marketplace.services import purchase_listing


class MarketListingListView(ListAPIView):
    serializer_class = MarketListingSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = _active_listing_queryset()
        seller = self.request.query_params.get("seller")
        card_variant = self.request.query_params.get("card_variant")
        status = self.request.query_params.get("status")
        price_min = self.request.query_params.get("price_min")
        price_max = self.request.query_params.get("price_max")

        if seller:
            queryset = queryset.filter(seller_id=seller)
        if card_variant:
            queryset = queryset.filter(inventory_item__card_variant_id=card_variant)
        if status and status != MarketListing.Status.ACTIVE:
            queryset = queryset.none()
        if price_min:
            queryset = queryset.filter(unit_price__gte=price_min)
        if price_max:
            queryset = queryset.filter(unit_price__lte=price_max)

        return queryset


class MarketListingDetailView(RetrieveAPIView):
    serializer_class = MarketListingSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return _active_listing_queryset()


class MySalesHistoryView(ListAPIView):
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return _order_history_queryset().filter(seller=self.request.user)


class MyPurchaseHistoryView(ListAPIView):
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return _order_history_queryset().filter(buyer=self.request.user)


class BuyListingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        listing = get_object_or_404(MarketListing.objects.all(), pk=pk)
        serializer = BuyListingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = purchase_listing(
                buyer=request.user,
                listing=listing,
                quantity=serializer.validated_data["quantity"],
            )
        except DjangoValidationError as error:
            return Response({"detail": error.messages}, status=status.HTTP_400_BAD_REQUEST)

        order = _order_history_queryset().get(pk=order.pk)
        return Response(PurchaseOrderSerializer(order).data, status=status.HTTP_201_CREATED)


def _active_listing_queryset():
    return (
        MarketListing.objects.filter(
            status=MarketListing.Status.ACTIVE,
            quantity_available__gt=0,
        )
        .select_related(
            "seller",
            "inventory_item__card_variant__card",
            "inventory_item__card_variant__set",
        )
        .order_by("-created_at", "id")
    )


def _order_history_queryset():
    line_queryset = PurchaseOrderLine.objects.select_related(
        "listing",
        "card_variant__card",
        "card_variant__set",
    )
    return (
        PurchaseOrder.objects.select_related("buyer", "seller")
        .prefetch_related(Prefetch("lines", queryset=line_queryset))
        .order_by("-created_at", "id")
    )
