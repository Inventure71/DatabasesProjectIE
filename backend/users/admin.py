from django.contrib import admin

from users.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "display_name", "country", "created_at", "updated_at")
    search_fields = ("user__username", "display_name", "country")
    readonly_fields = ("created_at", "updated_at")
