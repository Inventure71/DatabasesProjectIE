from django.urls import path

from inventory.views import (
    AddInventoryItemView,
    MyInventoryListView,
    RemoveInventoryQuantityView,
    UpdateInventoryItemView,
)

urlpatterns = [
    path("my/", MyInventoryListView.as_view(), name="inventory-my-list"),
    path("my/add/", AddInventoryItemView.as_view(), name="inventory-my-add"),
    path("my/<int:pk>/update/", UpdateInventoryItemView.as_view(), name="inventory-my-update"),
    path("my/<int:pk>/remove/", RemoveInventoryQuantityView.as_view(), name="inventory-my-remove"),
]
