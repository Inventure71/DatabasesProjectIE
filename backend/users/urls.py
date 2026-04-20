from django.urls import path

from users.views import CurrentUserView

urlpatterns = [
    path("me/", CurrentUserView.as_view(), name="users-me"),
]
