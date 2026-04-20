from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.models import InventoryItem
from inventory.serializers import (
    AddInventoryItemSerializer,
    InventoryItemSerializer,
    InventoryUpdateSerializer,
    RemoveInventoryQuantitySerializer,
)
from inventory.services import (
    add_inventory_item,
    decrease_quantity,
    increase_quantity,
    release_reserved_quantity,
    reserve_quantity,
)


class MyInventoryListView(ListAPIView):
    serializer_class = InventoryItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return _user_inventory_queryset(self.request.user)


class AddInventoryItemView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AddInventoryItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = add_inventory_item(
            owner=request.user,
            card_variant=serializer.validated_data["card_variant"],
            condition=serializer.validated_data["condition"],
            quantity=serializer.validated_data["quantity"],
            purchase_price=serializer.validated_data.get("purchase_price"),
            actor=request.user,
        )
        return Response(InventoryItemSerializer(item).data, status=status.HTTP_201_CREATED)


class UpdateInventoryItemView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        item = get_object_or_404(_user_inventory_queryset(request.user), pk=pk)
        serializer = InventoryUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            item = _apply_inventory_action(
                item=item,
                action=serializer.validated_data["action"],
                quantity=serializer.validated_data["quantity"],
                actor=request.user,
            )
        except DjangoValidationError as error:
            return Response({"detail": error.messages}, status=status.HTTP_400_BAD_REQUEST)

        return Response(InventoryItemSerializer(item).data)


class RemoveInventoryQuantityView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        item = get_object_or_404(_user_inventory_queryset(request.user), pk=pk)
        serializer = RemoveInventoryQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            item = decrease_quantity(
                item=item,
                quantity=serializer.validated_data["quantity"],
                actor=request.user,
                note="Removed through inventory API",
            )
        except DjangoValidationError as error:
            return Response({"detail": error.messages}, status=status.HTTP_400_BAD_REQUEST)

        return Response(InventoryItemSerializer(item).data)


def _user_inventory_queryset(user):
    return (
        InventoryItem.objects.filter(owner=user)
        .select_related("card_variant__card", "card_variant__set")
        .order_by("card_variant__card__name", "condition")
    )


def _apply_inventory_action(*, item, action, quantity, actor):
    if action == InventoryUpdateSerializer.Action.INCREASE:
        return increase_quantity(item=item, quantity=quantity, actor=actor)
    if action == InventoryUpdateSerializer.Action.DECREASE:
        return decrease_quantity(item=item, quantity=quantity, actor=actor)
    if action == InventoryUpdateSerializer.Action.RESERVE:
        return reserve_quantity(item=item, quantity=quantity, actor=actor)
    if action == InventoryUpdateSerializer.Action.RELEASE:
        return release_reserved_quantity(item=item, quantity=quantity, actor=actor)

    raise DjangoValidationError("Unsupported inventory action.")
