from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("", include("frontend.urls")),
    path("admin/", admin.site.urls),
    path("api/users/", include("users.urls")),
    path("api/catalog/", include("catalog.urls")),
    path("api/inventory/", include("inventory.urls")),
    path("api/marketplace/", include("marketplace.urls")),
    path("api/pricing/", include("pricing.urls")),
    path("mock-api/", include("frontend.mock_api.urls")),
]
