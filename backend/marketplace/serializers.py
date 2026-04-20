from rest_framework import serializers

from catalog.models import CardVariant
from marketplace.models import MarketListing, PurchaseOrder, PurchaseOrderLine


class MarketplaceUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()


class MarketplaceCardSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class MarketplaceCardSetSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    code = serializers.CharField()


class MarketplaceCardVariantSerializer(serializers.ModelSerializer):
    card = MarketplaceCardSerializer(read_only=True)
    set = MarketplaceCardSetSerializer(read_only=True)

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


class MarketListingSerializer(serializers.ModelSerializer):
    seller = MarketplaceUserSerializer(read_only=True)
    card_variant = MarketplaceCardVariantSerializer(source="inventory_item.card_variant", read_only=True)
    condition = serializers.CharField(source="inventory_item.condition", read_only=True)

    class Meta:
        model = MarketListing
        fields = (
            "id",
            "seller",
            "card_variant",
            "condition",
            "status",
            "quantity",
            "quantity_available",
            "unit_price",
            "currency",
        )


class PurchaseOrderLineSerializer(serializers.ModelSerializer):
    card_variant = MarketplaceCardVariantSerializer(read_only=True)
    line_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseOrderLine
        fields = (
            "id",
            "listing",
            "card_variant",
            "quantity",
            "unit_price",
            "line_total",
        )


class PurchaseOrderSerializer(serializers.ModelSerializer):
    buyer = MarketplaceUserSerializer(read_only=True)
    seller = MarketplaceUserSerializer(read_only=True)
    lines = PurchaseOrderLineSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = (
            "id",
            "buyer",
            "seller",
            "status",
            "total_amount",
            "currency",
            "created_at",
            "lines",
        )


class BuyListingSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)
