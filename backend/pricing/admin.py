from django.contrib import admin

from pricing.models import PriceSnapshot


@admin.register(PriceSnapshot)
class PriceSnapshotAdmin(admin.ModelAdmin):
    list_display = ("card_variant", "price", "currency", "source_name", "captured_at")
    list_select_related = ("card_variant__card", "card_variant__set")
    list_filter = ("currency", "source_name", "captured_at")
    search_fields = (
        "card_variant__card__name",
        "card_variant__set__name",
        "card_variant__collector_number",
        "source_name",
    )
    autocomplete_fields = ("card_variant",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-captured_at", "-id")
