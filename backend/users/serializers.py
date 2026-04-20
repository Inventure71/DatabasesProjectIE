from django.contrib.auth import get_user_model
from rest_framework import serializers

from users.models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ("display_name", "bio", "country", "avatar_url")


class CurrentUserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = get_user_model()
        fields = ("id", "username", "email", "profile")
