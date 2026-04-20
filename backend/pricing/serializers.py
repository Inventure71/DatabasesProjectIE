from rest_framework import serializers

from pricing.models import PriceSnapshot


class PriceSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceSnapshot
        fields = (
            "id",
            "card_variant",
            "price",
            "currency",
            "source_name",
            "captured_at",
        )


class CollectionValueSerializer(serializers.Serializer):
    total_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()
