from rest_framework import serializers

from catalog.models import Card, CardGame, CardImage, CardSet, CardVariant


class CardGameSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = CardGame
        fields = ("id", "name", "slug")


class CardSetSerializer(serializers.ModelSerializer):
    game = CardGameSummarySerializer(read_only=True)

    class Meta:
        model = CardSet
        fields = ("id", "game", "name", "code", "release_date", "description")


class CardImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardImage
        fields = ("image_url", "image_hash", "width", "height")


class CardSummarySerializer(serializers.ModelSerializer):
    game = CardGameSummarySerializer(read_only=True)

    class Meta:
        model = Card
        fields = ("id", "game", "name", "card_type", "subtype")


class CardVariantSummarySerializer(serializers.ModelSerializer):
    set = CardSetSerializer(read_only=True)

    class Meta:
        model = CardVariant
        fields = (
            "id",
            "set",
            "collector_number",
            "rarity",
            "finish",
            "language",
            "edition_label",
            "is_first_edition",
            "current_value",
        )


class CardListSerializer(serializers.ModelSerializer):
    game = CardGameSummarySerializer(read_only=True)

    class Meta:
        model = Card
        fields = ("id", "game", "name", "card_type", "subtype", "hp")


class CardDetailSerializer(serializers.ModelSerializer):
    game = CardGameSummarySerializer(read_only=True)
    variants = CardVariantSummarySerializer(many=True, read_only=True)

    class Meta:
        model = Card
        fields = (
            "id",
            "game",
            "name",
            "card_type",
            "subtype",
            "description",
            "artist_name",
            "attack",
            "defense",
            "hp",
            "variants",
        )


class CardVariantDetailSerializer(serializers.ModelSerializer):
    card = CardSummarySerializer(read_only=True)
    set = CardSetSerializer(read_only=True)
    image = CardImageSerializer(read_only=True)

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
            "edition_label",
            "is_first_edition",
            "current_value",
            "image",
        )
