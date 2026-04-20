from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from catalog.models import Card, CardGame, CardImage, CardSet, CardVariant
from inventory.models import InventoryItem
from inventory.services import add_inventory_item
from marketplace.models import MarketListing, PurchaseOrder
from marketplace.services import create_listing
from pricing.services import record_price_snapshot


class FrontendAuthFlowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="auth-user",
            password="auth-password",
        )

    def test_login_authenticates_session_and_navbar_posts_logout(self):
        login_response = self.client.post(
            reverse("login"),
            {"username": "auth-user", "password": "auth-password"},
        )

        self.assertRedirects(login_response, reverse("home"))

        current_user_response = self.client.get(reverse("users-me"))
        self.assertEqual(current_user_response.status_code, 200)
        self.assertEqual(current_user_response.json()["username"], "auth-user")

        home_response = self.client.get(reverse("home"))
        self.assertContains(home_response, "auth-user")
        self.assertContains(home_response, f'action="{reverse("logout")}"')
        self.assertContains(home_response, 'method="post"')

    def test_logout_post_clears_session(self):
        self.client.force_login(self.user)

        logout_response = self.client.post(reverse("logout"))

        self.assertRedirects(logout_response, reverse("home"))
        current_user_response = self.client.get(reverse("users-me"))
        self.assertEqual(current_user_response.status_code, 403)


class FrontendBackendApiWiringTests(TestCase):
    def setUp(self):
        self.seller = get_user_model().objects.create_user(
            username="frontend-seller",
            password="test-password",
        )
        self.buyer = get_user_model().objects.create_user(
            username="frontend-buyer",
            password="test-password",
        )
        self.game = CardGame.objects.create(name="Backend TCG", slug="backend-tcg")
        self.card_set = CardSet.objects.create(game=self.game, name="Backend Set", code="BACK")
        self.card = Card.objects.create(game=self.game, name="Backend Dragon")
        self.variant = CardVariant.objects.create(
            card=self.card,
            set=self.card_set,
            collector_number="1/99",
            rarity=CardVariant.Rarity.RARE,
            finish=CardVariant.Finish.HOLO,
            current_value=Decimal("42.50"),
        )
        CardImage.objects.create(
            card_variant=self.variant,
            image_url="https://example.com/backend-dragon.png",
        )
        self.seller_inventory = add_inventory_item(
            owner=self.seller,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=3,
            actor=self.seller,
        )
        self.listing = create_listing(
            seller=self.seller,
            inventory_item=self.seller_inventory,
            quantity=2,
            unit_price=Decimal("50.00"),
        )
        record_price_snapshot(
            card_variant=self.variant,
            price=Decimal("42.50"),
            source_name="frontend-test",
        )

    def test_catalog_page_uses_real_backend_catalog_data(self):
        response = self.client.get(reverse("catalog"), {"q": "Backend Dragon"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Backend Dragon")
        self.assertContains(response, "Backend Set")
        self.assertContains(response, "42.50")

    def test_catalog_page_paginates_card_results_in_database(self):
        for index in range(1, 13):
            card = Card.objects.create(
                game=self.game,
                name=f"Catalog Page {index:02d}",
            )
            CardVariant.objects.create(
                card=card,
                set=self.card_set,
                collector_number=f"{index + 1}/99",
            )

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("catalog"), {"page": "2", "page_size": "5"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Catalog Page 05")
        self.assertContains(response, "Page 2 of 3")
        self.assertNotContains(response, "Catalog Page 10")
        self.assertTrue(
            any("LIMIT 5" in query["sql"].upper() for query in queries.captured_queries),
            "Expected the catalog query to apply the page size in SQL.",
        )

    def test_home_search_form_submits_to_catalog_search(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'action="{reverse("catalog")}"')

    def test_home_page_limits_featured_queries_in_database(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        limited_queries = [
            query["sql"]
            for query in queries.captured_queries
            if "LIMIT 6" in query["sql"].upper()
        ]
        self.assertGreaterEqual(len(limited_queries), 2)

    def test_marketplace_page_uses_real_backend_listing_data(self):
        response = self.client.get(reverse("listings"), {"q": "Backend Dragon"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Backend Dragon")
        self.assertContains(response, "frontend-seller")
        self.assertContains(response, "50.00")

    def test_card_detail_uses_real_backend_price_history_and_listings(self):
        response = self.client.get(reverse("card_detail", kwargs={"card_id": self.card.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Backend Dragon")
        self.assertContains(response, "frontend-test")
        self.assertContains(response, "frontend-seller")

    def test_listing_detail_post_buys_through_backend_purchase_workflow(self):
        self.client.force_login(self.buyer)

        response = self.client.post(
            reverse("listing_detail", kwargs={"listing_id": self.listing.pk}),
            {"quantity": "1"},
        )
        self.listing.refresh_from_db()
        self.seller_inventory.refresh_from_db()

        self.assertRedirects(response, reverse("home"))
        self.assertEqual(PurchaseOrder.objects.count(), 1)
        self.assertEqual(self.listing.quantity_available, 1)
        self.assertEqual(self.seller_inventory.quantity, 2)
        self.assertTrue(InventoryItem.objects.filter(owner=self.buyer, card_variant=self.variant).exists())

    def test_frontend_backend_api_services_cover_authenticated_backend_apis(self):
        from frontend.services.backend_api import (
            add_inventory_item_for_user,
            get_collection_value,
            get_current_user,
            list_my_inventory,
            list_my_purchases,
            list_my_sales,
            remove_inventory_quantity_for_user,
            update_inventory_item_for_user,
        )

        user_data = get_current_user(self.buyer)
        added_item = add_inventory_item_for_user(
            user=self.buyer,
            card_variant_id=self.variant.id,
            condition=InventoryItem.Condition.LIGHTLY_PLAYED,
            quantity=2,
            purchase_price=Decimal("12.00"),
        )
        updated_item = update_inventory_item_for_user(
            user=self.buyer,
            item_id=added_item["id"],
            action="RESERVE",
            quantity=1,
        )
        removed_item = remove_inventory_quantity_for_user(
            user=self.buyer,
            item_id=added_item["id"],
            quantity=1,
        )

        self.client.force_login(self.buyer)
        self.client.post(reverse("listing_detail", kwargs={"listing_id": self.listing.pk}), {"quantity": "1"})

        self.assertEqual(user_data["username"], "frontend-buyer")
        self.assertEqual(len(list_my_inventory(self.buyer)), 2)
        self.assertEqual(updated_item["reserved_quantity"], 1)
        self.assertEqual(removed_item["quantity"], 1)
        self.assertEqual(get_collection_value(self.buyer)["currency"], "EUR")
        self.assertEqual(len(list_my_purchases(self.buyer)), 1)
        self.assertEqual(len(list_my_sales(self.seller)), 1)
