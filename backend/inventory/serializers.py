from rest_framework import serializers

from catalog.models import CardVariant
from inventory.models import InventoryItem


class InventoryCardSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class InventoryCardSetSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    code = serializers.CharField()


class InventoryCardVariantSerializer(serializers.ModelSerializer):
    card = InventoryCardSerializer(read_only=True)
    set = InventoryCardSetSerializer(read_only=True)

    class Meta:
        model = CardVariant
        fields = (
            "id",
            "card",
            "set",
            "collector_number",
            "rarity",
            "finish",
            "language",
        )


class InventoryItemSerializer(serializers.ModelSerializer):
    card_variant = InventoryCardVariantSerializer(read_only=True)
    available_quantity = serializers.IntegerField(read_only=True)

    class Meta:
        model = InventoryItem
        fields = (
            "id",
            "card_variant",
            "condition",
            "quantity",
            "reserved_quantity",
            "available_quantity",
            "is_for_sale",
            "acquired_at",
            "purchase_price",
        )


class AddInventoryItemSerializer(serializers.Serializer):
    card_variant_id = serializers.PrimaryKeyRelatedField(
        queryset=CardVariant.objects.all(),
        source="card_variant",
    )
    condition = serializers.ChoiceField(choices=InventoryItem.Condition.choices)
    quantity = serializers.IntegerField(min_value=1)
    purchase_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        allow_null=True,
    )


class InventoryUpdateSerializer(serializers.Serializer):
    class Action:
        INCREASE = "INCREASE"
        DECREASE = "DECREASE"
        RESERVE = "RESERVE"
        RELEASE = "RELEASE"

    action = serializers.ChoiceField(
        choices=(Action.INCREASE, Action.DECREASE, Action.RESERVE, Action.RELEASE)
    )
    quantity = serializers.IntegerField(min_value=1)


class RemoveInventoryQuantitySerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
