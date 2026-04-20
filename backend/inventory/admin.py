from django.contrib import admin

from inventory.models import InventoryHistory, InventoryItem


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "owner",
        "card_variant",
        "condition",
        "quantity",
        "reserved_quantity",
        "available_quantity",
        "is_for_sale",
    )
    list_filter = ("condition", "is_for_sale", "card_variant__set")
    search_fields = ("owner__username", "card_variant__card__name", "card_variant__collector_number")
    readonly_fields = ("created_at", "updated_at", "available_quantity")


@admin.register(InventoryHistory)
class InventoryHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "inventory_item", "change_type", "quantity_delta", "created_by", "created_at")
    list_filter = ("change_type",)
    search_fields = ("inventory_item__owner__username", "inventory_item__card_variant__card__name", "note")
    readonly_fields = ("created_at",)
