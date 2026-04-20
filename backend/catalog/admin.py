from django.contrib import admin

from catalog.models import Card, CardGame, CardImage, CardSet, CardVariant


@admin.register(CardGame)
class CardGameAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "created_at", "updated_at")
    search_fields = ("name", "slug")
    readonly_fields = ("created_at", "updated_at")


@admin.register(CardSet)
class CardSetAdmin(admin.ModelAdmin):
    list_display = ("id", "game", "name", "code", "release_date")
    list_select_related = ("game",)
    list_filter = ("game",)
    search_fields = ("name", "code", "game__name")
    autocomplete_fields = ("game",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("id", "game", "name", "card_type", "subtype", "hp")
    list_select_related = ("game",)
    list_filter = ("game", "card_type", "subtype")
    search_fields = ("name", "description", "artist_name")
    autocomplete_fields = ("game",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(CardVariant)
class CardVariantAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "card",
        "set",
        "collector_number",
        "rarity",
        "finish",
        "language",
        "current_value",
    )
    list_select_related = ("card", "set")
    list_filter = ("set", "rarity", "finish", "language", "is_first_edition")
    search_fields = ("card__name", "set__name", "collector_number")
    autocomplete_fields = ("card", "set")
    readonly_fields = ("created_at", "updated_at")


@admin.register(CardImage)
class CardImageAdmin(admin.ModelAdmin):
    list_display = ("id", "card_variant", "image_url", "width", "height")
    list_select_related = ("card_variant__card", "card_variant__set")
    search_fields = ("card_variant__card__name", "image_url", "image_hash")
    autocomplete_fields = ("card_variant",)
    readonly_fields = ("created_at", "updated_at")
