from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import Card, CardGame, CardSet, CardVariant
from inventory.models import InventoryHistory, InventoryItem
from inventory.services import (
    add_inventory_item,
    decrease_quantity,
    increase_quantity,
    merge_purchased_item,
    release_reserved_quantity,
    reserve_quantity,
)


class InventoryModelTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="collector",
            password="test-password",
        )
        self.actor = get_user_model().objects.create_user(
            username="admin-user",
            password="test-password",
        )
        game = CardGame.objects.create(name="Pokemon", slug="pokemon")
        card_set = CardSet.objects.create(game=game, name="Base Set", code="BASE")
        card = Card.objects.create(game=game, name="Charizard")
        self.variant = CardVariant.objects.create(
            card=card,
            set=card_set,
            collector_number="4/102",
            rarity=CardVariant.Rarity.RARE,
            finish=CardVariant.Finish.HOLO,
        )

    def test_inventory_item_belongs_to_owner_and_card_variant(self):
        item = InventoryItem.objects.create(
            owner=self.owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=2,
            purchase_price=Decimal("100.00"),
        )

        self.assertEqual(item.owner, self.owner)
        self.assertEqual(item.card_variant, self.variant)
        self.assertEqual(item.available_quantity, 2)
        self.assertIn(item, self.owner.inventory_items.all())
        self.assertIn(item, self.variant.inventory_items.all())

    def test_same_owner_variant_condition_is_one_aggregate_inventory_bucket(self):
        InventoryItem.objects.create(
            owner=self.owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=1,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            InventoryItem.objects.create(
                owner=self.owner,
                card_variant=self.variant,
                condition=InventoryItem.Condition.NEAR_MINT,
                quantity=1,
            )

        self.assertEqual(
            InventoryItem.objects.filter(
                owner=self.owner,
                card_variant=self.variant,
                condition=InventoryItem.Condition.NEAR_MINT,
            ).count(),
            1,
        )

    def test_quantity_can_be_zero_after_stock_is_sold(self):
        item = InventoryItem(
            owner=self.owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=0,
        )

        item.full_clean()

    def test_quantity_cannot_be_negative(self):
        item = InventoryItem(
            owner=self.owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=-1,
        )

        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_reserved_quantity_cannot_be_negative_or_exceed_quantity(self):
        negative_reserved = InventoryItem(
            owner=self.owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=2,
            reserved_quantity=-1,
        )
        too_much_reserved = InventoryItem(
            owner=self.owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=2,
            reserved_quantity=3,
        )

        with self.assertRaises(ValidationError):
            negative_reserved.full_clean()
        with self.assertRaises(ValidationError):
            too_much_reserved.full_clean()

    def test_purchase_price_cannot_be_negative(self):
        item = InventoryItem(
            owner=self.owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=1,
            purchase_price=Decimal("-1.00"),
        )

        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_inventory_history_records_stock_change(self):
        item = InventoryItem.objects.create(
            owner=self.owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=2,
        )

        history = InventoryHistory.objects.create(
            inventory_item=item,
            change_type=InventoryHistory.ChangeType.INCREASE,
            quantity_delta=2,
            created_by=self.actor,
            note="Initial import",
        )

        self.assertEqual(history.inventory_item, item)
        self.assertEqual(history.created_by, self.actor)
        self.assertEqual(history.quantity_delta, 2)
        self.assertIn(history, item.history_entries.all())


class InventoryServiceTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="collector",
            password="test-password",
        )
        self.buyer = get_user_model().objects.create_user(
            username="buyer",
            password="test-password",
        )
        game = CardGame.objects.create(name="Pokemon", slug="pokemon")
        card_set = CardSet.objects.create(game=game, name="Base Set", code="BASE")
        card = Card.objects.create(game=game, name="Charizard")
        self.variant = CardVariant.objects.create(
            card=card,
            set=card_set,
            collector_number="4/102",
            rarity=CardVariant.Rarity.RARE,
            finish=CardVariant.Finish.HOLO,
        )

    def test_add_inventory_item_creates_item_and_history(self):
        item = add_inventory_item(
            owner=self.owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=2,
            purchase_price=Decimal("100.00"),
            actor=self.owner,
            note="Initial import",
        )

        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.available_quantity, 2)
        history = item.history_entries.get()
        self.assertEqual(history.change_type, InventoryHistory.ChangeType.ADD)
        self.assertEqual(history.quantity_delta, 2)
        self.assertEqual(history.created_by, self.owner)

    def test_add_inventory_item_merges_same_owner_variant_condition_into_one_bucket(self):
        first_item = add_inventory_item(
            owner=self.owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=1,
            actor=self.owner,
        )

        second_item = add_inventory_item(
            owner=self.owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=2,
            actor=self.owner,
        )

        first_item.refresh_from_db()
        self.assertEqual(first_item, second_item)
        self.assertEqual(first_item.quantity, 3)
        self.assertEqual(
            list(first_item.history_entries.order_by("created_at").values_list("change_type", "quantity_delta")),
            [
                (InventoryHistory.ChangeType.ADD, 1),
                (InventoryHistory.ChangeType.INCREASE, 2),
            ],
        )

    def test_increase_quantity_updates_quantity_and_history(self):
        item = add_inventory_item(
            owner=self.owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=1,
        )

        increase_quantity(item=item, quantity=4, actor=self.owner, note="Found more")
        item.refresh_from_db()

        self.assertEqual(item.quantity, 5)
        latest_history = item.history_entries.order_by("-created_at").first()
        self.assertEqual(latest_history.change_type, InventoryHistory.ChangeType.INCREASE)
        self.assertEqual(latest_history.quantity_delta, 4)
        self.assertEqual(latest_history.note, "Found more")

    def test_decrease_quantity_updates_quantity_and_history(self):
        item = add_inventory_item(
            owner=self.owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=5,
        )

        decrease_quantity(item=item, quantity=2, actor=self.owner)
        item.refresh_from_db()

        self.assertEqual(item.quantity, 3)
        latest_history = item.history_entries.order_by("-created_at").first()
        self.assertEqual(latest_history.change_type, InventoryHistory.ChangeType.DECREASE)
        self.assertEqual(latest_history.quantity_delta, -2)

    def test_decrease_quantity_rejects_removing_reserved_stock(self):
        item = add_inventory_item(
            owner=self.owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=5,
        )
        reserve_quantity(item=item, quantity=4, actor=self.owner)

        with self.assertRaises(ValidationError):
            decrease_quantity(item=item, quantity=2, actor=self.owner)

    def test_reserve_and_release_quantity(self):
        item = add_inventory_item(
            owner=self.owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=5,
        )

        reserve_quantity(item=item, quantity=3, actor=self.owner)
        item.refresh_from_db()
        self.assertEqual(item.reserved_quantity, 3)
        self.assertEqual(item.available_quantity, 2)

        release_reserved_quantity(item=item, quantity=2, actor=self.owner)
        item.refresh_from_db()
        self.assertEqual(item.reserved_quantity, 1)
        self.assertEqual(item.available_quantity, 4)

        history_types = list(item.history_entries.order_by("created_at").values_list("change_type", flat=True))
        self.assertEqual(
            history_types,
            [
                InventoryHistory.ChangeType.ADD,
                InventoryHistory.ChangeType.RESERVE,
                InventoryHistory.ChangeType.RELEASE,
            ],
        )

    def test_reserve_quantity_rejects_more_than_available(self):
        item = add_inventory_item(
            owner=self.owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=2,
        )

        with self.assertRaises(ValidationError):
            reserve_quantity(item=item, quantity=3, actor=self.owner)

    def test_release_reserved_quantity_rejects_more_than_reserved(self):
        item = add_inventory_item(
            owner=self.owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=2,
        )

        with self.assertRaises(ValidationError):
            release_reserved_quantity(item=item, quantity=1, actor=self.owner)

    def test_merge_purchased_item_adds_stock_to_buyer_inventory(self):
        item = merge_purchased_item(
            buyer=self.buyer,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=1,
            actor=self.buyer,
            purchase_price=Decimal("120.00"),
        )

        self.assertEqual(item.owner, self.buyer)
        self.assertEqual(item.quantity, 1)
        history = item.history_entries.get()
        self.assertEqual(history.change_type, InventoryHistory.ChangeType.PURCHASE)
        self.assertEqual(history.quantity_delta, 1)


class InventoryAdminTests(TestCase):
    def test_inventory_item_admin_is_optimized_for_owner_and_variant_inspection(self):
        item_admin = admin.site._registry[InventoryItem]

        self.assertEqual(item_admin.list_select_related, ("owner", "card_variant__card", "card_variant__set"))
        self.assertEqual(item_admin.autocomplete_fields, ("owner", "card_variant"))
        self.assertIn("available_quantity", item_admin.readonly_fields)
        self.assertNotIn("is_for_sale", item_admin.list_display)
        self.assertNotIn("is_for_sale", item_admin.list_filter)

    def test_inventory_history_admin_is_read_only_audit_log(self):
        history_admin = admin.site._registry[InventoryHistory]

        self.assertFalse(history_admin.has_add_permission(None))
        self.assertFalse(history_admin.has_delete_permission(None))
        self.assertEqual(
            history_admin.readonly_fields,
            ("inventory_item", "change_type", "quantity_delta", "created_by", "note", "created_at"),
        )


class InventoryApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        game = CardGame.objects.create(name="Inventory API TCG", slug="inventory-api-tcg")
        card_set = CardSet.objects.create(game=game, name="Inventory API Set", code="INVAPI")
        card = Card.objects.create(game=game, name="Inventory API Dragon")
        cls.variant = CardVariant.objects.create(
            card=card,
            set=card_set,
            collector_number="1/99",
            rarity=CardVariant.Rarity.RARE,
            finish=CardVariant.Finish.HOLO,
            language="en",
        )

    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="collector-api",
            password="test-password",
        )
        self.other_user = get_user_model().objects.create_user(
            username="other-api",
            password="test-password",
        )
        self.variant = self.__class__.variant

    def test_anonymous_user_cannot_list_inventory(self):
        response = self.client.get(reverse("inventory-my-list"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_returns_only_authenticated_user_inventory(self):
        own_item = add_inventory_item(
            owner=self.owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=2,
        )
        add_inventory_item(
            owner=self.other_user,
            card_variant=self.variant,
            condition=InventoryItem.Condition.LIGHTLY_PLAYED,
            quantity=1,
        )
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(reverse("inventory-my-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], own_item.id)
        self.assertEqual(response.data[0]["card_variant"]["card"]["name"], "Inventory API Dragon")
        self.assertEqual(response.data[0]["available_quantity"], 2)
        self.assertNotIn("is_for_sale", response.data[0])

    def test_add_inventory_endpoint_uses_service_and_writes_history(self):
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            reverse("inventory-my-add"),
            {
                "card_variant_id": self.variant.id,
                "condition": InventoryItem.Condition.NEAR_MINT,
                "quantity": 2,
                "purchase_price": "100.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        item = InventoryItem.objects.get(owner=self.owner, card_variant=self.variant)
        self.assertEqual(item.quantity, 2)
        history = item.history_entries.get()
        self.assertEqual(history.change_type, InventoryHistory.ChangeType.ADD)
        self.assertEqual(history.created_by, self.owner)

    def test_add_inventory_endpoint_merges_same_owner_variant_condition(self):
        add_inventory_item(
            owner=self.owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=1,
            actor=self.owner,
        )
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            reverse("inventory-my-add"),
            {
                "card_variant_id": self.variant.id,
                "condition": InventoryItem.Condition.NEAR_MINT,
                "quantity": 2,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        item = InventoryItem.objects.get(owner=self.owner, card_variant=self.variant)
        self.assertEqual(item.quantity, 3)
        self.assertEqual(item.history_entries.count(), 2)
        self.assertEqual(response.data["quantity"], 3)

    def test_update_endpoint_can_increase_reserve_and_release_stock(self):
        item = add_inventory_item(
            owner=self.owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=2,
        )
        self.client.force_authenticate(user=self.owner)

        increase_response = self.client.post(
            reverse("inventory-my-update", kwargs={"pk": item.pk}),
            {"action": "INCREASE", "quantity": 3},
            format="json",
        )
        reserve_response = self.client.post(
            reverse("inventory-my-update", kwargs={"pk": item.pk}),
            {"action": "RESERVE", "quantity": 4},
            format="json",
        )
        release_response = self.client.post(
            reverse("inventory-my-update", kwargs={"pk": item.pk}),
            {"action": "RELEASE", "quantity": 1},
            format="json",
        )
        item.refresh_from_db()

        self.assertEqual(increase_response.status_code, status.HTTP_200_OK)
        self.assertEqual(reserve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(release_response.status_code, status.HTTP_200_OK)
        self.assertEqual(item.quantity, 5)
        self.assertEqual(item.reserved_quantity, 3)
        self.assertEqual(item.available_quantity, 2)

    def test_remove_endpoint_reduces_available_stock_and_writes_history(self):
        item = add_inventory_item(
            owner=self.owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=4,
        )
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            reverse("inventory-my-remove", kwargs={"pk": item.pk}),
            {"quantity": 2},
            format="json",
        )
        item.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(item.quantity, 2)
        latest_history = item.history_entries.order_by("-created_at").first()
        self.assertEqual(latest_history.change_type, InventoryHistory.ChangeType.DECREASE)
        self.assertEqual(latest_history.created_by, self.owner)

    def test_user_cannot_update_another_users_inventory(self):
        item = add_inventory_item(
            owner=self.other_user,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=2,
        )
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            reverse("inventory-my-update", kwargs={"pk": item.pk}),
            {"action": "INCREASE", "quantity": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_inventory_update_returns_bad_request(self):
        item = add_inventory_item(
            owner=self.owner,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=2,
        )
        self.client.force_authenticate(user=self.owner)

        response = self.client.post(
            reverse("inventory-my-update", kwargs={"pk": item.pk}),
            {"action": "RESERVE", "quantity": 3},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
