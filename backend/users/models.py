from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class UserProfile(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    display_name = models.CharField(max_length=80)
    bio = models.TextField(blank=True)
    country = models.CharField(max_length=80, blank=True)
    avatar_url = models.URLField(blank=True)

    class Meta:
        db_table = "user_profile"

    def __str__(self):
        return self.display_name
