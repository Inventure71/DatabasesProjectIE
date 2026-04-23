from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.http import QueryDict
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from catalog.models import Card, CardGame, CardImage, CardSet, CardVariant
from inventory.models import InventoryItem
from inventory.services import add_inventory_item
from marketplace.models import MarketListing, PurchaseOrder
from marketplace.services import create_listing, purchase_listing
from pricing.models import PriceSnapshot
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

    def test_catalog_page_defaults_to_shared_card_album_view(self):
        response = self.client.get(reverse("catalog"), {"q": "Backend Dragon"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="browser-view-toggle"')
        self.assertContains(response, 'class="browser-view-toggle__link browser-view-toggle__link--active"')
        self.assertContains(response, "Card")
        self.assertContains(response, "Collection Book Cover")
        self.assertContains(response, "Shelf")
        self.assertContains(response, "album-card-grid")
        self.assertContains(response, "Album Page")

    def test_catalog_page_can_switch_to_set_books_and_game_shelves(self):
        set_response = self.client.get(reverse("catalog"), {"view": "set"})
        shelf_response = self.client.get(reverse("catalog"), {"view": "shelf"})

        self.assertEqual(set_response.status_code, 200)
        self.assertContains(set_response, 'class="collection-book-shelf"')
        self.assertContains(set_response, "Collection Book Cover")
        self.assertContains(set_response, "Backend Set")

        self.assertEqual(shelf_response.status_code, 200)
        self.assertContains(shelf_response, 'class="game-shelf-grid"')
        self.assertContains(shelf_response, "Backend TCG")

    def test_browser_view_links_reset_filters_that_conflict_with_target_view(self):
        response = self.client.get(
            reverse("catalog"),
            {
                "view": "card",
                "game": "Backend TCG",
                "set": "Backend Set",
                "q": "Backend Dragon",
            },
        )

        options = {
            option["label"]: QueryDict(option["query"])
            for option in response.context["browser"]["view_options"]
        }

        self.assertEqual(options["Collection Book Cover"].get("view"), "set")
        self.assertIsNone(options["Collection Book Cover"].get("set"))
        self.assertEqual(options["Collection Book Cover"].get("game"), "Backend TCG")

        self.assertEqual(options["Shelf"].get("view"), "shelf")
        self.assertIsNone(options["Shelf"].get("game"))
        self.assertEqual(options["Shelf"].get("set"), "Backend Set")

    def test_catalog_set_filter_requires_selected_game(self):
        other_game = CardGame.objects.create(name="Other TCG", slug="other-tcg")
        other_set = CardSet.objects.create(game=other_game, name="Other Set", code="OTHER")
        other_card = Card.objects.create(game=other_game, name="Other Dragon")
        CardVariant.objects.create(card=other_card, set=other_set, collector_number="1/10")

        default_response = self.client.get(reverse("catalog"))
        selected_game_response = self.client.get(reverse("catalog"), {"game": "Backend TCG"})

        self.assertEqual(default_response.status_code, 200)
        self.assertEqual(default_response.context["sets"], [])
        self.assertContains(default_response, "Choose a game first")

        self.assertEqual(selected_game_response.status_code, 200)
        self.assertEqual(selected_game_response.context["sets"], ["Backend Set"])
        self.assertContains(selected_game_response, "Backend Set")
        self.assertNotIn("Other Set", selected_game_response.context["sets"])

    def test_catalog_ignores_stale_set_filter_from_another_game(self):
        other_game = CardGame.objects.create(name="Other TCG", slug="other-tcg")
        CardSet.objects.create(game=other_game, name="Other Set", code="OTHER")

        response = self.client.get(
            reverse("catalog"),
            {
                "game": "Backend TCG",
                "set": "Other Set",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Backend Dragon")
        self.assertEqual(response.context["sets"], ["Backend Set"])
        self.assertNotIn("Other Set", response.context["sets"])

    def test_sidebar_search_inputs_switch_shared_browser_forms_to_card_view(self):
        self.client.force_login(self.seller)
        responses = [
            self.client.get(reverse("catalog"), {"view": "shelf"}),
            self.client.get(reverse("catalog"), {"view": "shelf", "available": "1"}),
            self.client.get(reverse("collection"), {"view": "shelf"}),
        ]

        for response in responses:
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'name="view" value="shelf"')
            self.assertContains(response, 'oninput="this.form.elements.view.value=\'card\'"')

    def test_shared_browser_filter_and_view_navigation_targets_browser_anchor(self):
        response = self.client.get(
            reverse("catalog"),
            {
                "view": "set",
                "game": "Backend TCG",
                "set": "Backend Set",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="browser"')
        self.assertContains(response, 'action="/catalog/#browser"')
        self.assertContains(response, 'href="/catalog/#browser"')
        self.assertContains(response, 'href="?view=card&amp;game=Backend+TCG&amp;set=Backend+Set#browser"')
        self.assertContains(response, 'href="?view=set&amp;game=Backend+TCG#browser"')
        self.assertContains(response, 'href="?view=shelf&amp;set=Backend+Set#browser"')

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

    def test_catalog_search_uses_database_side_mysql_safe_filtering(self):
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("catalog"), {"q": "Backend Dragon"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Backend Dragon")
        sql = "\n".join(query["sql"] for query in queries.captured_queries).upper()
        self.assertIn("LIKE", sql)
        self.assertNotIn("TO_TSVECTOR", sql)
        self.assertNotIn("PLAINTO_TSQUERY", sql)

    def test_catalog_set_browser_uses_database_grouping_for_book_summaries(self):
        extra_card = Card.objects.create(game=self.game, name="Backend Phoenix")
        CardVariant.objects.create(
            card=extra_card,
            set=self.card_set,
            collector_number="2/99",
            current_value=Decimal("11.00"),
        )

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("catalog"), {"view": "set"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Backend Set")
        self.assertTrue(
            any(
                "GROUP BY" in query["sql"].upper() and "CARD_VARIANT" in query["sql"].upper()
                for query in queries.captured_queries
            ),
            "Expected catalog set summaries to be grouped by the database.",
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

    def test_home_featured_cards_fill_missing_sale_slots_from_catalog(self):
        fallback_card_names = []
        for index in range(1, 7):
            card = Card.objects.create(game=self.game, name=f"Fallback Feature {index:02d}")
            fallback_card_names.append(card.name)
            CardVariant.objects.create(
                card=card,
                set=self.card_set,
                collector_number=f"F{index}/99",
                rarity=CardVariant.Rarity.COMMON,
                current_value=Decimal(index),
            )

        purchase_listing(buyer=self.buyer, listing=self.listing, quantity=1)

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        featured_names = [card["name"] for card in response.context["featured_cards"]]
        self.assertEqual(len(featured_names), 6)
        self.assertEqual(featured_names[0], "Backend Dragon")
        self.assertEqual(len(featured_names), len(set(featured_names)))
        self.assertTrue(any(name in featured_names for name in fallback_card_names))
        self.assertTrue(
            any(
                "CARD_VARIANT" in query["sql"].upper()
                and "NOT" in query["sql"].upper()
                and " IN " in query["sql"].upper()
                and "LIMIT 5" in query["sql"].upper()
                for query in queries
            ),
            "Expected fallback featured cards to exclude sold variants and limit missing slots in SQL.",
        )

    def test_home_page_prioritizes_latest_listings_above_featured_cards(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertLess(content.index("Latest Listings"), content.index("Featured Cards"))
        self.assertContains(response, f'href="{reverse("catalog")}?available=1#browser"')

    def test_database_query_explainers_render_on_backend_backed_pages(self):
        self.client.force_login(self.seller)

        responses = [
            self.client.get(reverse("home")),
            self.client.get(reverse("catalog"), {"q": "Backend Dragon", "available": "1"}),
            self.client.get(reverse("card_variant_detail", kwargs={"variant_id": self.variant.pk})),
            self.client.get(reverse("collection"), {"view": "card"}),
            self.client.get(reverse("listing_detail", kwargs={"listing_id": self.listing.pk})),
        ]

        for response in responses:
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'data-query-help-open')
            self.assertContains(response, "Database query walkthrough")

        self.assertContains(responses[0], "Latest listings query")
        self.assertContains(responses[0], "Featured cards query")
        self.assertContains(responses[1], "Catalog browser query")
        self.assertContains(responses[2], "Your copies query")
        self.assertContains(responses[2], "Card active listings query")
        self.assertContains(responses[2], "Price history query")
        self.assertContains(responses[2], "Similar cards query")
        self.assertContains(responses[3], "Collection summary query")
        self.assertContains(responses[3], "Owned inventory browser query")
        self.assertContains(responses[4], "Listing detail query")

    def test_query_explainer_javascript_is_loaded_inline(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "queryHelpOpen")

    def test_home_page_showcases_most_expensive_card_sold_this_month(self):
        old_expensive_sale = purchase_listing(
            buyer=self.buyer,
            listing=self.listing,
            quantity=1,
        )
        PurchaseOrder.objects.filter(pk=old_expensive_sale.pk).update(
            created_at=timezone.now() - timezone.timedelta(days=40),
        )

        current_month_card = Card.objects.create(game=self.game, name="Monthly Trophy Dragon")
        current_month_variant = CardVariant.objects.create(
            card=current_month_card,
            set=self.card_set,
            collector_number="2/99",
            rarity=CardVariant.Rarity.SECRET_RARE,
            finish=CardVariant.Finish.HOLO,
            current_value=Decimal("120.00"),
        )
        CardImage.objects.create(
            card_variant=current_month_variant,
            image_url="https://example.com/monthly-trophy-dragon.png",
        )
        current_month_inventory = add_inventory_item(
            owner=self.seller,
            card_variant=current_month_variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=1,
            actor=self.seller,
        )
        current_month_listing = create_listing(
            seller=self.seller,
            inventory_item=current_month_inventory,
            quantity=1,
            unit_price=Decimal("120.00"),
        )
        purchase_listing(
            buyer=self.buyer,
            listing=current_month_listing,
            quantity=1,
        )

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Most expensive card sold this month")
        self.assertContains(response, "Monthly Trophy Dragon")
        self.assertContains(response, "$120.00")
        self.assertContains(response, 'id="kinetic-card-preview-title">Monthly Trophy Dragon')
        self.assertNotContains(response, 'id="kinetic-card-preview-title">Backend Dragon')

    def test_card_surfaces_reuse_kinetic_card_component(self):
        home_response = self.client.get(reverse("home"))
        catalog_response = self.client.get(reverse("catalog"), {"q": "Backend Dragon"})
        available_response = self.client.get(reverse("catalog"), {"q": "Backend Dragon", "available": "1"})
        card_detail_response = self.client.get(reverse("card_detail", kwargs={"card_id": self.card.pk}))
        listing_detail_response = self.client.get(reverse("listing_detail", kwargs={"listing_id": self.listing.pk}))
        self.client.force_login(self.seller)
        collection_response = self.client.get(reverse("collection"))

        self.assertEqual(home_response.status_code, 200)
        self.assertContains(home_response, 'data-kinetic-card')
        self.assertContains(home_response, 'class="kinetic-card__tilt"')
        self.assertContains(home_response, "Backend Dragon")

        self.assertEqual(catalog_response.status_code, 200)
        self.assertContains(catalog_response, 'class="album-card-grid"')
        self.assertContains(catalog_response, 'data-kinetic-card')

        self.assertEqual(available_response.status_code, 200)
        self.assertContains(available_response, 'data-kinetic-card')

        self.assertEqual(card_detail_response.status_code, 200)
        self.assertContains(card_detail_response, 'data-kinetic-card')

        self.assertEqual(listing_detail_response.status_code, 200)
        self.assertContains(listing_detail_response, 'data-kinetic-card')

        self.assertEqual(collection_response.status_code, 200)
        self.assertContains(collection_response, 'data-kinetic-card')

    def test_catalog_links_to_exact_variant_detail_route(self):
        second_variant = CardVariant.objects.create(
            card=self.card,
            set=self.card_set,
            collector_number="2/99",
            rarity=CardVariant.Rarity.UNCOMMON,
            finish=CardVariant.Finish.NORMAL,
            current_value=Decimal("13.25"),
        )
        CardImage.objects.create(
            card_variant=second_variant,
            image_url="https://example.com/backend-dragon-normal.png",
        )

        response = self.client.get(reverse("catalog"), {"q": "Backend Dragon"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("card_variant_detail", kwargs={"variant_id": self.variant.id}))
        self.assertContains(response, reverse("card_variant_detail", kwargs={"variant_id": second_variant.id}))

    def test_collection_page_requires_login(self):
        response = self.client.get(reverse("collection"))

        self.assertRedirects(response, f"{reverse('login')}?next={reverse('collection')}")

    def test_listings_route_redirects_to_catalog_with_available_filter(self):
        response = self.client.get(reverse("listings"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"{reverse('catalog')}?available=1#browser")

    def test_listings_route_preserves_existing_filters_when_redirecting_to_catalog(self):
        response = self.client.get(
            reverse("listings"),
            {"q": "Backend Dragon", "view": "shelf", "sort": "price_asc"},
        )

        self.assertEqual(response.status_code, 302)
        redirected = QueryDict(response["Location"].split("?", 1)[1].split("#", 1)[0])
        self.assertEqual(response["Location"].split("#", 1)[1], "browser")
        self.assertEqual(redirected.get("q"), "Backend Dragon")
        self.assertEqual(redirected.get("view"), "shelf")
        self.assertEqual(redirected.get("available"), "1")
        self.assertIsNone(redirected.get("sort"))

    def test_catalog_available_filter_shows_only_cards_with_active_listings(self):
        unlisted_card = Card.objects.create(game=self.game, name="Binder Turtle")
        CardVariant.objects.create(
            card=unlisted_card,
            set=self.card_set,
            collector_number="2/99",
            rarity=CardVariant.Rarity.COMMON,
            current_value=Decimal("8.00"),
        )

        response = self.client.get(reverse("catalog"), {"available": "1"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Backend Dragon")
        self.assertNotContains(response, "Binder Turtle")
        self.assertContains(response, 'name="available"')
        self.assertContains(response, 'value="1"')
        self.assertContains(response, "checked")
        self.assertContains(response, 'class="browser-view-toggle"')
        self.assertContains(response, "album-card-grid")

    def test_listing_cards_use_listed_by_copy_for_active_listings(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Listed by")
        self.assertNotContains(response, "Sold by")

    def test_listing_and_album_card_images_link_to_detail_pages(self):
        home_response = self.client.get(reverse("home"))
        catalog_response = self.client.get(reverse("catalog"), {"q": "Backend Dragon"})

        self.assertEqual(home_response.status_code, 200)
        self.assertContains(home_response, f'href="{reverse("listing_detail", kwargs={"listing_id": self.listing.pk})}"')
        self.assertContains(home_response, 'class="listing-card__image-wrap"')

        self.assertEqual(catalog_response.status_code, 200)
        self.assertContains(catalog_response, f'href="{reverse("card_variant_detail", kwargs={"variant_id": self.variant.pk})}" class="album-card-slot__image album-card-slot__image-link"')

    def test_collection_listed_filter_shows_only_authenticated_users_active_listings(self):
        buyer_inventory = add_inventory_item(
            owner=self.buyer,
            card_variant=self.variant,
            condition=InventoryItem.Condition.DAMAGED,
            quantity=1,
            actor=self.buyer,
        )
        create_listing(
            seller=self.buyer,
            inventory_item=buyer_inventory,
            quantity=1,
            unit_price=Decimal("61.00"),
        )
        self.client.force_login(self.seller)

        response = self.client.get(reverse("collection"), {"view": "card", "my_listings": "listed"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Collection")
        self.assertContains(response, "Backend Dragon")
        self.assertContains(response, "Listed")
        self.assertContains(response, "2 listed")
        self.assertNotContains(response, "frontend-buyer")
        self.assertNotContains(response, "61.00")

    def test_navbar_keeps_listing_management_inside_collection(self):
        self.client.force_login(self.seller)

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Collection")
        self.assertNotContains(response, "My Listings")

    def test_my_listings_page_requires_login(self):
        response = self.client.get(reverse("my_listings"))

        self.assertRedirects(response, f"{reverse('login')}?next={reverse('my_listings')}")

    def test_my_listings_redirects_authenticated_users_to_collection_listed_filter(self):
        self.client.force_login(self.seller)

        response = self.client.get(reverse("my_listings"))

        self.assertRedirects(response, f"{reverse('collection')}?view=card&my_listings=listed#browser")

    def test_collection_page_organizes_owned_cards_as_set_books_with_album_filters(self):
        jungle_set = CardSet.objects.create(game=self.game, name="Jungle", code="JUNG")
        jungle_card = Card.objects.create(game=self.game, name="Jungle Cat")
        jungle_variant = CardVariant.objects.create(
            card=jungle_card,
            set=jungle_set,
            collector_number="4/64",
            rarity=CardVariant.Rarity.UNCOMMON,
            current_value=Decimal("12.00"),
        )
        CardImage.objects.create(
            card_variant=jungle_variant,
            image_url="https://example.com/jungle-cat.png",
        )
        add_inventory_item(
            owner=self.seller,
            card_variant=jungle_variant,
            condition=InventoryItem.Condition.LIGHTLY_PLAYED,
            quantity=1,
            actor=self.seller,
        )
        self.client.force_login(self.seller)

        response = self.client.get(reverse("collection"), {"view": "card", "game": "Backend TCG", "set": "Jungle"})
        default_response = self.client.get(reverse("collection"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="browser-view-toggle"')
        self.assertContains(response, "album-card-grid")
        self.assertContains(response, "Album Page")
        self.assertContains(response, "Jungle")
        self.assertContains(response, 'name="q"')
        self.assertContains(response, 'name="rarity"')
        self.assertContains(response, 'name="language"')
        self.assertContains(response, "Jungle Cat")
        self.assertContains(response, "Backend Set")
        self.assertContains(response, 'class="album-card-grid album-card-grid--sleeves"')
        self.assertNotContains(response, 'class="collection-sell-form collection-sell-form--album"')
        self.assertContains(default_response, 'class="browser-view-toggle"')
        self.assertContains(default_response, 'class="collection-book-shelf"')
        self.assertContains(default_response, "Collection Book Cover")

    def test_collection_page_marks_partial_listings_without_gray_overlay(self):
        unlisted_card = Card.objects.create(game=self.game, name="Binder Turtle")
        unlisted_variant = CardVariant.objects.create(
            card=unlisted_card,
            set=self.card_set,
            collector_number="2/99",
            rarity=CardVariant.Rarity.COMMON,
            current_value=Decimal("8.00"),
        )
        CardImage.objects.create(
            card_variant=unlisted_variant,
            image_url="https://example.com/binder-turtle.png",
        )
        add_inventory_item(
            owner=self.seller,
            card_variant=unlisted_variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=1,
            actor=self.seller,
        )
        self.client.force_login(self.seller)

        response = self.client.get(reverse("collection"), {"view": "card"})
        listed_response = self.client.get(reverse("collection"), {"view": "card", "my_listings": "listed"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="my_listings"')
        self.assertContains(response, "My Listings")
        self.assertContains(response, "Backend Dragon")
        self.assertContains(response, "Binder Turtle")
        self.assertContains(response, "Listed")
        self.assertContains(response, "3 owned")
        self.assertContains(response, "1 owned")
        self.assertContains(response, "2 listed")
        self.assertNotContains(response, "album-card-slot--listed")
        self.assertContains(response, "album-card-sleeve__pills")
        self.assertContains(response, "album-card-sleeve__pill--owned")
        self.assertContains(response, "album-card-sleeve__pill--listed")
        self.assertNotContains(response, "album-card-sleeve__listing")

        self.assertEqual(listed_response.status_code, 200)
        self.assertContains(listed_response, "Backend Dragon")
        self.assertContains(listed_response, "3 owned")
        self.assertContains(listed_response, "2 listed")
        self.assertNotContains(listed_response, "Binder Turtle")

    def test_collection_page_grays_out_fully_listed_inventory(self):
        fully_listed_card = Card.objects.create(game=self.game, name="Fully Listed Owl")
        fully_listed_variant = CardVariant.objects.create(
            card=fully_listed_card,
            set=self.card_set,
            collector_number="3/99",
            rarity=CardVariant.Rarity.COMMON,
            current_value=Decimal("11.00"),
        )
        CardImage.objects.create(
            card_variant=fully_listed_variant,
            image_url="https://example.com/fully-listed-owl.png",
        )
        inventory_item = add_inventory_item(
            owner=self.seller,
            card_variant=fully_listed_variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=2,
            actor=self.seller,
        )
        create_listing(
            seller=self.seller,
            inventory_item=inventory_item,
            quantity=2,
            unit_price=Decimal("15.00"),
        )
        self.client.force_login(self.seller)

        response = self.client.get(reverse("collection"), {"view": "card", "q": "Fully Listed Owl"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fully Listed Owl")
        self.assertContains(response, "album-card-slot--listed")
        self.assertContains(response, "2 owned")
        self.assertContains(response, "2 listed")

    def test_collection_listed_filter_uses_album_filters_for_active_listings(self):
        jungle_set = CardSet.objects.create(game=self.game, name="Jungle", code="JUNG")
        jungle_card = Card.objects.create(game=self.game, name="Jungle Cat")
        jungle_variant = CardVariant.objects.create(
            card=jungle_card,
            set=jungle_set,
            collector_number="4/64",
            rarity=CardVariant.Rarity.UNCOMMON,
            current_value=Decimal("12.00"),
        )
        CardImage.objects.create(
            card_variant=jungle_variant,
            image_url="https://example.com/jungle-cat.png",
        )
        jungle_inventory = add_inventory_item(
            owner=self.seller,
            card_variant=jungle_variant,
            condition=InventoryItem.Condition.LIGHTLY_PLAYED,
            quantity=2,
            actor=self.seller,
        )
        create_listing(
            seller=self.seller,
            inventory_item=jungle_inventory,
            quantity=1,
            unit_price=Decimal("18.00"),
        )
        self.client.force_login(self.seller)

        response = self.client.get(
            reverse("collection"),
            {"view": "card", "game": "Backend TCG", "set": "Jungle", "my_listings": "listed"},
        )
        default_response = self.client.get(reverse("collection"), {"view": "card", "my_listings": "listed"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="browser-view-toggle"')
        self.assertContains(response, "album-card-grid")
        self.assertContains(response, "Album Page")
        self.assertContains(response, 'name="q"')
        self.assertContains(response, 'name="rarity"')
        self.assertContains(response, 'name="language"')
        self.assertContains(response, "Jungle Cat")
        self.assertContains(response, "Listed")
        self.assertContains(response, "1 listed")
        self.assertNotContains(response, "Backend Dragon")
        self.assertContains(default_response, 'class="browser-view-toggle"')
        self.assertContains(default_response, "album-card-grid")

    def test_collection_summary_uses_database_aggregation(self):
        self.client.force_login(self.seller)

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("collection"), {"view": "card"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["summary"]["total_quantity"], 3)
        self.assertTrue(
            any(
                "SUM(" in query["sql"].upper()
                and "RESERVED_QUANTITY" in query["sql"].upper()
                and "INVENTORY_ITEM" in query["sql"].upper()
                for query in queries.captured_queries
            ),
            "Expected collection totals to be computed with SQL aggregates.",
        )

    def test_collection_card_browser_limits_owned_inventory_in_database(self):
        for index in range(1, 15):
            card = Card.objects.create(game=self.game, name=f"Owned Page {index:02d}")
            variant = CardVariant.objects.create(
                card=card,
                set=self.card_set,
                collector_number=f"{index + 10}/99",
                current_value=Decimal("2.00"),
            )
            add_inventory_item(
                owner=self.seller,
                card_variant=variant,
                condition=InventoryItem.Condition.NEAR_MINT,
                quantity=1,
                actor=self.seller,
            )
        self.client.force_login(self.seller)

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("collection"), {"view": "card"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Album Page")
        self.assertTrue(
            any(
                "INVENTORY_ITEM" in query["sql"].upper() and "LIMIT 12" in query["sql"].upper()
                for query in queries.captured_queries
            ),
            "Expected collection card browsing to apply the visible page limit in SQL.",
        )

    def test_card_detail_uses_real_backend_price_history_and_listings(self):
        response = self.client.get(reverse("card_detail", kwargs={"card_id": self.card.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Backend Dragon")
        self.assertContains(response, "frontend-test")
        self.assertContains(response, "frontend-seller")

    def test_card_detail_limits_price_history_in_database(self):
        for index in range(30):
            PriceSnapshot.objects.create(
                card_variant=self.variant,
                price=Decimal("1.00") + Decimal(index),
                source_name=f"history-{index}",
                captured_at=timezone.now() - timezone.timedelta(days=index + 1),
            )

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse("card_variant_detail", kwargs={"variant_id": self.variant.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "history-0")
        self.assertNotContains(response, "history-29")
        self.assertTrue(
            any(
                "PRICE_SNAPSHOT" in query["sql"].upper() and "LIMIT 24" in query["sql"].upper()
                for query in queries.captured_queries
            ),
            "Expected price history to apply the display limit in SQL.",
        )

    def test_variant_detail_uses_requested_variant(self):
        second_variant = CardVariant.objects.create(
            card=self.card,
            set=self.card_set,
            collector_number="2/99",
            rarity=CardVariant.Rarity.UNCOMMON,
            finish=CardVariant.Finish.NORMAL,
            current_value=Decimal("13.25"),
        )
        CardImage.objects.create(
            card_variant=second_variant,
            image_url="https://example.com/backend-dragon-normal.png",
        )
        self.client.force_login(self.buyer)

        response = self.client.get(reverse("card_variant_detail", kwargs={"variant_id": second_variant.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "13.25")
        self.assertContains(response, f'name="card_variant_id" value="{second_variant.id}"')

    def test_card_detail_uses_scoped_inventory_lookup(self):
        self.client.force_login(self.seller)

        with patch("frontend.views.list_my_inventory", side_effect=AssertionError("unscoped inventory used")):
            response = self.client.get(reverse("card_detail", kwargs={"card_id": self.card.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your Copies")

    def test_card_detail_exposes_add_to_collection_without_purchase_price(self):
        self.client.force_login(self.buyer)

        response = self.client.get(reverse("card_detail", kwargs={"card_id": self.card.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Own this card?")
        self.assertContains(response, "Add a copy you already own to your collection.")
        self.assertContains(response, "detail-own-card__summary")
        self.assertContains(response, "detail-own-card__panel")
        self.assertContains(response, "Add to Collection")
        self.assertContains(response, f'action="{reverse("add_to_collection")}"')
        self.assertContains(response, f'name="card_variant_id" value="{self.variant.id}"')
        self.assertContains(response, 'name="condition"')
        self.assertContains(response, 'name="quantity"')
        self.assertNotContains(response, 'name="purchase_price"')

    def test_add_to_collection_post_creates_owned_inventory_from_card_detail(self):
        self.client.force_login(self.buyer)

        response = self.client.post(
            reverse("add_to_collection"),
            {
                "card_id": str(self.card.id),
                "card_variant_id": str(self.variant.id),
                "condition": InventoryItem.Condition.LIGHTLY_PLAYED,
                "quantity": "2",
            },
        )

        added_item = InventoryItem.objects.get(
            owner=self.buyer,
            card_variant=self.variant,
            condition=InventoryItem.Condition.LIGHTLY_PLAYED,
        )
        self.assertRedirects(
            response,
            f"{reverse('card_variant_detail', kwargs={'variant_id': self.variant.pk})}?added={added_item.id}",
        )
        self.assertEqual(added_item.quantity, 2)
        self.assertIsNone(added_item.purchase_price)

    def test_add_to_collection_post_merges_existing_inventory_bucket(self):
        existing_item = add_inventory_item(
            owner=self.buyer,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=1,
            actor=self.buyer,
        )
        self.client.force_login(self.buyer)

        response = self.client.post(
            reverse("add_to_collection"),
            {
                "card_id": str(self.card.id),
                "card_variant_id": str(self.variant.id),
                "condition": InventoryItem.Condition.NEAR_MINT,
                "quantity": "3",
            },
        )

        existing_item.refresh_from_db()
        self.assertRedirects(
            response,
            f"{reverse('card_variant_detail', kwargs={'variant_id': self.variant.pk})}?added={existing_item.id}",
        )
        self.assertEqual(existing_item.quantity, 4)
        self.assertEqual(
            InventoryItem.objects.filter(
                owner=self.buyer,
                card_variant=self.variant,
                condition=InventoryItem.Condition.NEAR_MINT,
            ).count(),
            1,
        )

    def test_card_detail_allows_owner_to_create_listing_from_owned_inventory(self):
        unlisted_inventory = add_inventory_item(
            owner=self.seller,
            card_variant=self.variant,
            condition=InventoryItem.Condition.LIGHTLY_PLAYED,
            quantity=1,
            actor=self.seller,
        )
        self.client.force_login(self.seller)

        response = self.client.get(reverse("card_detail", kwargs={"card_id": self.card.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your Copies")
        self.assertContains(response, "Listed Copies")
        self.assertContains(response, "2 listed")
        self.assertContains(response, "$50.00")
        self.assertContains(response, 'name="inventory_item_id"')
        self.assertContains(response, f'name="inventory_item_id" value="{unlisted_inventory.id}"')
        self.assertContains(response, f'name="inventory_item_id" value="{self.seller_inventory.id}"')
        self.assertContains(response, "List Copy")

        post_response = self.client.post(
            reverse("card_detail", kwargs={"card_id": self.card.pk}),
            {
                "inventory_item_id": unlisted_inventory.id,
                "quantity": "1",
                "unit_price": "73.25",
            },
        )

        listing = MarketListing.objects.filter(
            seller=self.seller,
            inventory_item=unlisted_inventory,
            unit_price=Decimal("73.25"),
        ).latest("id")
        self.assertRedirects(post_response, f"{reverse('card_variant_detail', kwargs={'variant_id': self.variant.pk})}?listed={listing.id}")

    def test_fully_sold_inventory_does_not_remain_visible_as_owned(self):
        sold_inventory = add_inventory_item(
            owner=self.seller,
            card_variant=self.variant,
            condition=InventoryItem.Condition.LIGHTLY_PLAYED,
            quantity=1,
            actor=self.seller,
        )
        sold_listing = create_listing(
            seller=self.seller,
            inventory_item=sold_inventory,
            quantity=1,
            unit_price=Decimal("58.00"),
        )
        self.client.force_login(self.buyer)

        response = self.client.post(
            reverse("listing_detail", kwargs={"listing_id": sold_listing.pk}),
            {"quantity": "1"},
        )
        sold_inventory.refresh_from_db()
        self.client.force_login(self.seller)
        collection_response = self.client.get(reverse("collection"), {"view": "card"})
        detail_response = self.client.get(reverse("card_detail", kwargs={"card_id": self.card.pk}))

        self.assertRedirects(response, reverse("home"))
        self.assertEqual(sold_inventory.quantity, 0)
        self.assertNotContains(collection_response, "Lightly Played")
        self.assertNotContains(detail_response, f'name="inventory_item_id" value="{sold_inventory.id}"')

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
            create_marketplace_listing_for_user,
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
        sellable_item = add_inventory_item_for_user(
            user=self.buyer,
            card_variant_id=self.variant.id,
            condition=InventoryItem.Condition.DAMAGED,
            quantity=1,
        )
        listing = create_marketplace_listing_for_user(
            user=self.buyer,
            inventory_item_id=sellable_item["id"],
            quantity=1,
            unit_price=Decimal("60.00"),
        )

        self.client.force_login(self.buyer)
        self.client.post(reverse("listing_detail", kwargs={"listing_id": self.listing.pk}), {"quantity": "1"})

        self.assertEqual(user_data["username"], "frontend-buyer")
        self.assertEqual(len(list_my_inventory(self.buyer)), 3)
        self.assertEqual(updated_item["reserved_quantity"], 1)
        self.assertEqual(removed_item["quantity"], 1)
        self.assertEqual(listing["seller"]["username"], "frontend-buyer")
        self.assertEqual(get_collection_value(self.buyer)["currency"], "EUR")
        self.assertEqual(len(list_my_purchases(self.buyer)), 1)
        self.assertEqual(len(list_my_sales(self.seller)), 1)

    def test_collection_page_shows_owned_inventory_and_collection_value(self):
        self.client.force_login(self.seller)

        response = self.client.get(reverse("collection"), {"view": "card"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My Collection")
        self.assertContains(response, "Backend Dragon")
        self.assertContains(response, "frontend-seller")
        self.assertContains(response, "127.50")
        self.assertContains(response, "Available")
        self.assertNotContains(response, "Sell")

    def test_collection_page_post_adds_inventory_to_aggregate_bucket(self):
        self.client.force_login(self.buyer)

        response = self.client.post(
            reverse("collection"),
            {
                "form_action": "add_inventory",
                "card_variant_id": str(self.variant.id),
                "condition": InventoryItem.Condition.NEAR_MINT,
                "quantity": "1",
                "purchase_price": "11.25",
            },
        )

        added_item = InventoryItem.objects.get(owner=self.buyer, card_variant=self.variant)
        self.assertRedirects(response, f"{reverse('collection')}?added={added_item.id}")
        self.assertEqual(added_item.quantity, 1)
        self.assertEqual(added_item.purchase_price, Decimal("11.25"))

    def test_collection_page_add_merges_duplicate_inventory_bucket(self):
        existing_item = add_inventory_item(
            owner=self.buyer,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=1,
            actor=self.buyer,
        )
        self.client.force_login(self.buyer)

        response = self.client.post(
            reverse("collection"),
            {
                "form_action": "add_inventory",
                "card_variant_id": str(self.variant.id),
                "condition": InventoryItem.Condition.NEAR_MINT,
                "quantity": "1",
            },
        )

        existing_item.refresh_from_db()
        self.assertRedirects(response, f"{reverse('collection')}?added={existing_item.id}")
        self.assertEqual(existing_item.quantity, 2)
        self.assertEqual(
            InventoryItem.objects.filter(
                owner=self.buyer,
                card_variant=self.variant,
                condition=InventoryItem.Condition.NEAR_MINT,
            ).count(),
            1,
        )

    def test_collection_page_post_creates_listing_from_owned_inventory(self):
        buyer_inventory = add_inventory_item(
            owner=self.buyer,
            card_variant=self.variant,
            condition=InventoryItem.Condition.LIGHTLY_PLAYED,
            quantity=2,
            actor=self.buyer,
        )
        self.client.force_login(self.buyer)

        response = self.client.post(
            reverse("collection"),
            {
                "inventory_item_id": buyer_inventory.id,
                "quantity": "1",
                "unit_price": "64.25",
            },
        )
        buyer_inventory.refresh_from_db()

        listing = MarketListing.objects.get(seller=self.buyer, inventory_item=buyer_inventory)
        self.assertRedirects(response, f"{reverse('collection')}?listed={listing.id}")
        self.assertEqual(listing.quantity, 1)
        self.assertEqual(listing.quantity_available, 1)
        self.assertEqual(listing.unit_price, Decimal("64.25"))
        self.assertEqual(buyer_inventory.reserved_quantity, 1)

    def test_collection_page_rejects_selling_more_than_available_inventory(self):
        self.client.force_login(self.seller)

        response = self.client.post(
            reverse("collection"),
            {
                "inventory_item_id": self.seller_inventory.id,
                "quantity": "2",
                "unit_price": "99.00",
            },
        )
        self.seller_inventory.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cannot list more than the available inventory quantity.")
        self.assertEqual(self.seller_inventory.reserved_quantity, 2)
        self.assertEqual(MarketListing.objects.filter(seller=self.seller).count(), 1)
