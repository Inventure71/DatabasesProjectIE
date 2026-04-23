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
    )
    list_select_related = ("owner", "card_variant__card", "card_variant__set")
    list_filter = ("condition", "card_variant__set")
    search_fields = ("owner__username", "card_variant__card__name", "card_variant__collector_number")
    autocomplete_fields = ("owner", "card_variant")
    readonly_fields = ("created_at", "updated_at", "available_quantity")


@admin.register(InventoryHistory)
class InventoryHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "inventory_item", "change_type", "quantity_delta", "created_by", "created_at")
    list_select_related = ("inventory_item__owner", "inventory_item__card_variant__card", "created_by")
    list_filter = ("change_type",)
    search_fields = ("inventory_item__owner__username", "inventory_item__card_variant__card__name", "note")
    readonly_fields = ("inventory_item", "change_type", "quantity_delta", "created_by", "note", "created_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
