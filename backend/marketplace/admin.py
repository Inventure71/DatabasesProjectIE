from django.contrib import admin

from marketplace.models import MarketListing, PurchaseOrder, PurchaseOrderLine


@admin.register(MarketListing)
class MarketListingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "seller",
        "inventory_item",
        "status",
        "quantity",
        "quantity_available",
        "unit_price",
        "currency",
    )
    list_select_related = ("seller", "inventory_item__card_variant__card", "inventory_item__card_variant__set")
    list_filter = ("status", "currency")
    search_fields = ("seller__username", "inventory_item__card_variant__card__name")
    autocomplete_fields = ("seller", "inventory_item")
    readonly_fields = ("created_at", "updated_at")


class PurchaseOrderLineInline(admin.TabularInline):
    model = PurchaseOrderLine
    readonly_fields = ("listing", "card_variant", "quantity", "unit_price")
    can_delete = False
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "buyer", "seller", "status", "total_amount", "currency", "created_at")
    list_select_related = ("buyer", "seller")
    list_filter = ("status", "currency")
    search_fields = ("buyer__username", "seller__username")
    autocomplete_fields = ("buyer", "seller")
    readonly_fields = ("created_at", "updated_at")
    inlines = (PurchaseOrderLineInline,)


@admin.register(PurchaseOrderLine)
class PurchaseOrderLineAdmin(admin.ModelAdmin):
    list_display = ("id", "purchase_order", "listing", "card_variant", "quantity", "unit_price")
    list_select_related = ("purchase_order", "listing", "card_variant__card", "card_variant__set")
    search_fields = ("card_variant__card__name",)
    readonly_fields = ("purchase_order", "listing", "card_variant", "quantity", "unit_price", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
