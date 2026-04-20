from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase

from users.models import UserProfile


class UserProfileModelTests(TestCase):
    def test_profile_belongs_to_one_user(self):
        user = get_user_model().objects.create_user(
            username="seller",
            password="test-password",
        )

        profile = UserProfile.objects.create(
            user=user,
            display_name="Seller One",
            country="Spain",
        )

        self.assertEqual(profile.user, user)
        self.assertEqual(user.profile, profile)

    def test_profile_uses_user_as_one_to_one_relation(self):
        field = UserProfile._meta.get_field("user")

        self.assertTrue(field.one_to_one)
        self.assertTrue(field.unique)
        self.assertEqual(field.remote_field.on_delete, models.CASCADE)

    def test_profile_string_uses_display_name(self):
        user = get_user_model().objects.create_user(
            username="collector",
            password="test-password",
        )

        profile = UserProfile.objects.create(
            user=user,
            display_name="Collector One",
            country="Italy",
        )

        self.assertEqual(str(profile), "Collector One")

    def test_profile_has_timestamps(self):
        user = get_user_model().objects.create_user(
            username="timestamp-user",
            password="test-password",
        )

        profile = UserProfile.objects.create(
            user=user,
            display_name="Timestamp User",
        )

        self.assertIsNotNone(profile.created_at)
        self.assertIsNotNone(profile.updated_at)

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

class CurrentUserEndpointTests(APITestCase):
    def test_anonymous_user_cannot_access_me_endpoint(self):
        response = self.client.get(reverse("users-me"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_can_read_own_user_and_profile(self):
        user = get_user_model().objects.create_user(
            username="buyer",
            email="buyer@example.com",
            password="test-password",
        )
        UserProfile.objects.create(
            user=user,
            display_name="Buyer One",
            country="Spain",
            bio="Collects rare cards.",
            avatar_url="https://example.com/avatar.png",
        )

        self.client.force_authenticate(user=user)

        response = self.client.get(reverse("users-me"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "id": user.id,
                "username": "buyer",
                "email": "buyer@example.com",
                "profile": {
                    "display_name": "Buyer One",
                    "bio": "Collects rare cards.",
                    "country": "Spain",
                    "avatar_url": "https://example.com/avatar.png",
                },
            },
        )
