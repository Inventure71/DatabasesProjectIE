from datetime import timedelta
from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import Card, CardGame, CardSet, CardVariant
from inventory.models import InventoryItem
from pricing.models import PriceSnapshot
from pricing.services import (
    estimate_collection_value,
    get_variant_price_history,
    record_price_snapshot,
    update_current_value_from_latest_snapshot,
)


class PricingTestCase(TestCase):
    def setUp(self):
        self.game = CardGame.objects.create(name="Pokemon", slug="pokemon-pricing")
        self.card_set = CardSet.objects.create(game=self.game, name="Base Set", code="BASE")
        self.card = Card.objects.create(game=self.game, name="Charizard")
        self.variant = CardVariant.objects.create(
            card=self.card,
            set=self.card_set,
            collector_number="4/102",
            rarity=CardVariant.Rarity.RARE,
            finish=CardVariant.Finish.HOLO,
        )


class PriceSnapshotModelTests(PricingTestCase):
    def test_price_snapshot_references_card_variant(self):
        snapshot = PriceSnapshot.objects.create(
            card_variant=self.variant,
            price=Decimal("125.50"),
            currency="EUR",
            source_name="manual",
        )

        self.assertEqual(snapshot.card_variant, self.variant)
        self.assertEqual(snapshot.price, Decimal("125.50"))
        self.assertEqual(snapshot.currency, "EUR")
        self.assertEqual(snapshot.source_name, "manual")
        self.assertIsNotNone(snapshot.captured_at)

    def test_price_snapshot_rejects_negative_price(self):
        snapshot = PriceSnapshot(
            card_variant=self.variant,
            price=Decimal("-1.00"),
            currency="EUR",
            source_name="manual",
        )

        with self.assertRaises(ValidationError):
            snapshot.full_clean()


class PricingServiceTests(PricingTestCase):
    def test_record_price_snapshot_stores_snapshot_and_updates_current_value(self):
        captured_at = timezone.now()

        snapshot = record_price_snapshot(
            card_variant=self.variant,
            price=Decimal("125.50"),
            currency="EUR",
            source_name="manual",
            captured_at=captured_at,
        )
        self.variant.refresh_from_db()

        self.assertEqual(snapshot.card_variant, self.variant)
        self.assertEqual(snapshot.price, Decimal("125.50"))
        self.assertEqual(snapshot.currency, "EUR")
        self.assertEqual(snapshot.source_name, "manual")
        self.assertEqual(snapshot.captured_at, captured_at)
        self.assertEqual(self.variant.current_value, Decimal("125.50"))

    def test_record_price_snapshot_can_skip_current_value_update(self):
        self.variant.current_value = Decimal("50.00")
        self.variant.save(update_fields=("current_value", "updated_at"))

        record_price_snapshot(
            card_variant=self.variant,
            price=Decimal("125.50"),
            currency="EUR",
            source_name="manual",
            update_current_value=False,
        )
        self.variant.refresh_from_db()

        self.assertEqual(self.variant.current_value, Decimal("50.00"))

    def test_update_current_value_uses_newest_snapshot(self):
        older_time = timezone.now() - timedelta(days=1)
        newer_time = timezone.now()
        PriceSnapshot.objects.create(
            card_variant=self.variant,
            price=Decimal("200.00"),
            currency="EUR",
            source_name="manual",
            captured_at=older_time,
        )
        PriceSnapshot.objects.create(
            card_variant=self.variant,
            price=Decimal("125.50"),
            currency="EUR",
            source_name="manual",
            captured_at=newer_time,
        )

        update_current_value_from_latest_snapshot(card_variant=self.variant)
        self.variant.refresh_from_db()

        self.assertEqual(self.variant.current_value, Decimal("125.50"))

    def test_update_current_value_rejects_variant_without_snapshots(self):
        with self.assertRaises(ValidationError):
            update_current_value_from_latest_snapshot(card_variant=self.variant)

    def test_get_variant_price_history_returns_newest_first(self):
        older = record_price_snapshot(
            card_variant=self.variant,
            price=Decimal("100.00"),
            source_name="manual",
            captured_at=timezone.now() - timedelta(days=1),
            update_current_value=False,
        )
        newer = record_price_snapshot(
            card_variant=self.variant,
            price=Decimal("125.50"),
            source_name="manual",
            captured_at=timezone.now(),
            update_current_value=False,
        )

        history = list(get_variant_price_history(card_variant=self.variant))

        self.assertEqual(history, [newer, older])

    def test_get_variant_price_history_can_limit_results(self):
        record_price_snapshot(
            card_variant=self.variant,
            price=Decimal("100.00"),
            source_name="manual",
            captured_at=timezone.now() - timedelta(days=1),
            update_current_value=False,
        )
        newer = record_price_snapshot(
            card_variant=self.variant,
            price=Decimal("125.50"),
            source_name="manual",
            captured_at=timezone.now(),
            update_current_value=False,
        )

        history = list(get_variant_price_history(card_variant=self.variant, limit=1))

        self.assertEqual(history, [newer])

    def test_estimate_collection_value_sums_owned_quantity_times_current_value(self):
        owner = get_user_model().objects.create_user(username="pricing-owner")
        self.variant.current_value = Decimal("125.50")
        self.variant.save(update_fields=("current_value", "updated_at"))
        InventoryItem.objects.create(
            owner=owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=2,
        )

        total_value = estimate_collection_value(owner=owner)

        self.assertEqual(total_value, Decimal("251.00"))


class PricingAdminTests(TestCase):
    def test_price_snapshot_admin_is_optimized_for_variant_inspection(self):
        snapshot_admin = admin.site._registry[PriceSnapshot]

        self.assertEqual(snapshot_admin.list_select_related, ("card_variant__card", "card_variant__set"))
        self.assertEqual(snapshot_admin.autocomplete_fields, ("card_variant",))
        self.assertIn("created_at", snapshot_admin.readonly_fields)
        self.assertIn("updated_at", snapshot_admin.readonly_fields)


class PricingApiTests(APITestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="pricing-api-owner")
        game = CardGame.objects.create(name="Pokemon", slug="pokemon-pricing-api")
        card_set = CardSet.objects.create(game=game, name="Base Set", code="BASE")
        card = Card.objects.create(game=game, name="Charizard")
        self.variant = CardVariant.objects.create(
            card=card,
            set=card_set,
            collector_number="4/102",
            rarity=CardVariant.Rarity.RARE,
            finish=CardVariant.Finish.HOLO,
        )

    def test_variant_price_history_endpoint_returns_newest_first(self):
        older = record_price_snapshot(
            card_variant=self.variant,
            price=Decimal("100.00"),
            source_name="manual",
            captured_at=timezone.now() - timedelta(days=1),
            update_current_value=False,
        )
        newer = record_price_snapshot(
            card_variant=self.variant,
            price=Decimal("125.50"),
            source_name="manual",
            captured_at=timezone.now(),
            update_current_value=False,
        )

        response = self.client.get(
            reverse("pricing-variant-history", kwargs={"variant_id": self.variant.pk})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([row["id"] for row in response.data], [newer.id, older.id])
        self.assertEqual(response.data[0]["price"], "125.50")
        self.assertEqual(response.data[0]["currency"], "EUR")
        self.assertEqual(response.data[0]["source_name"], "manual")

    def test_variant_price_history_endpoint_returns_not_found_for_missing_variant(self):
        response = self.client.get(reverse("pricing-variant-history", kwargs={"variant_id": 999999}))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_collection_value_endpoint_requires_authentication(self):
        response = self.client.get(reverse("pricing-my-collection-value"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_collection_value_endpoint_returns_authenticated_users_total(self):
        self.variant.current_value = Decimal("125.50")
        self.variant.save(update_fields=("current_value", "updated_at"))
        InventoryItem.objects.create(
            owner=self.owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=2,
        )
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(reverse("pricing-my-collection-value"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_value"], "251.00")
        self.assertEqual(response.data["currency"], "EUR")
