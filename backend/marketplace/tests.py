from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import Card, CardGame, CardSet, CardVariant
from inventory.models import InventoryHistory, InventoryItem
from marketplace.models import MarketListing, PurchaseOrder, PurchaseOrderLine
from marketplace.services import (
    cancel_listing,
    create_listing,
    mark_listing_sold_out,
    pause_listing,
    purchase_listing,
)
from pricing.models import PriceSnapshot


class MarketplaceModelTests(TestCase):
    def setUp(self):
        self.seller = get_user_model().objects.create_user(
            username="seller",
            password="test-password",
        )
        self.buyer = get_user_model().objects.create_user(
            username="buyer",
            password="test-password",
        )
        self.other_user = get_user_model().objects.create_user(
            username="other-user",
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
        self.inventory_item = InventoryItem.objects.create(
            owner=self.seller,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=5,
            reserved_quantity=0,
        )

    def test_listing_references_seller_owned_inventory(self):
        listing = MarketListing.objects.create(
            seller=self.seller,
            inventory_item=self.inventory_item,
            quantity=2,
            quantity_available=2,
            unit_price=Decimal("125.50"),
        )

        self.assertEqual(listing.seller, self.seller)
        self.assertEqual(listing.inventory_item, self.inventory_item)
        self.assertEqual(listing.inventory_item.card_variant, self.variant)
        self.assertEqual(listing.status, MarketListing.Status.ACTIVE)

    def test_listing_rejects_inventory_owned_by_another_user(self):
        listing = MarketListing(
            seller=self.other_user,
            inventory_item=self.inventory_item,
            quantity=1,
            quantity_available=1,
            unit_price=Decimal("100.00"),
        )

        with self.assertRaises(ValidationError):
            listing.full_clean()

    def test_listing_quantity_and_price_constraints_are_validated(self):
        zero_quantity = MarketListing(
            seller=self.seller,
            inventory_item=self.inventory_item,
            quantity=0,
            quantity_available=0,
            unit_price=Decimal("100.00"),
        )
        too_much_available = MarketListing(
            seller=self.seller,
            inventory_item=self.inventory_item,
            quantity=2,
            quantity_available=3,
            unit_price=Decimal("100.00"),
        )
        negative_price = MarketListing(
            seller=self.seller,
            inventory_item=self.inventory_item,
            quantity=1,
            quantity_available=1,
            unit_price=Decimal("-1.00"),
        )

        with self.assertRaises(ValidationError):
            zero_quantity.full_clean()
        with self.assertRaises(ValidationError):
            too_much_available.full_clean()
        with self.assertRaises(ValidationError):
            negative_price.full_clean()

    def test_sold_out_listing_must_have_no_available_quantity(self):
        listing = MarketListing(
            seller=self.seller,
            inventory_item=self.inventory_item,
            status=MarketListing.Status.SOLD_OUT,
            quantity=2,
            quantity_available=1,
            unit_price=Decimal("100.00"),
        )

        with self.assertRaises(ValidationError):
            listing.full_clean()

    def test_order_references_buyer_and_seller(self):
        order = PurchaseOrder.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            status=PurchaseOrder.Status.PENDING,
            total_amount=Decimal("251.00"),
        )

        self.assertEqual(order.buyer, self.buyer)
        self.assertEqual(order.seller, self.seller)
        self.assertEqual(order.status, PurchaseOrder.Status.PENDING)

    def test_order_rejects_same_buyer_and_seller(self):
        order = PurchaseOrder(
            buyer=self.seller,
            seller=self.seller,
            status=PurchaseOrder.Status.PENDING,
            total_amount=Decimal("100.00"),
        )

        with self.assertRaises(ValidationError):
            order.full_clean()

    def test_order_total_cannot_be_negative(self):
        order = PurchaseOrder(
            buyer=self.buyer,
            seller=self.seller,
            status=PurchaseOrder.Status.PENDING,
            total_amount=Decimal("-1.00"),
        )

        with self.assertRaises(ValidationError):
            order.full_clean()

    def test_order_line_snapshots_listing_variant_quantity_and_price(self):
        listing = MarketListing.objects.create(
            seller=self.seller,
            inventory_item=self.inventory_item,
            quantity=2,
            quantity_available=2,
            unit_price=Decimal("125.50"),
        )
        order = PurchaseOrder.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            total_amount=Decimal("251.00"),
        )
        line = PurchaseOrderLine.objects.create(
            purchase_order=order,
            listing=listing,
            card_variant=self.variant,
            quantity=2,
            unit_price=Decimal("125.50"),
        )

        self.assertEqual(line.purchase_order, order)
        self.assertEqual(line.listing, listing)
        self.assertEqual(line.card_variant, self.variant)
        self.assertEqual(line.quantity, 2)
        self.assertEqual(line.line_total, Decimal("251.00"))

    def test_order_line_quantity_and_price_constraints_are_validated(self):
        listing = MarketListing.objects.create(
            seller=self.seller,
            inventory_item=self.inventory_item,
            quantity=2,
            quantity_available=2,
            unit_price=Decimal("125.50"),
        )
        order = PurchaseOrder.objects.create(
            buyer=self.buyer,
            seller=self.seller,
            total_amount=Decimal("251.00"),
        )
        zero_quantity_line = PurchaseOrderLine(
            purchase_order=order,
            listing=listing,
            card_variant=self.variant,
            quantity=0,
            unit_price=Decimal("125.50"),
        )
        negative_price_line = PurchaseOrderLine(
            purchase_order=order,
            listing=listing,
            card_variant=self.variant,
            quantity=1,
            unit_price=Decimal("-1.00"),
        )

        with self.assertRaises(ValidationError):
            zero_quantity_line.full_clean()
        with self.assertRaises(ValidationError):
            negative_price_line.full_clean()

    def test_marketplace_foreign_key_shape_is_explicit(self):
        self.assertIsInstance(MarketListing._meta.get_field("seller"), models.ForeignKey)
        self.assertIsInstance(MarketListing._meta.get_field("inventory_item"), models.ForeignKey)
        self.assertIsInstance(PurchaseOrder._meta.get_field("buyer"), models.ForeignKey)
        self.assertIsInstance(PurchaseOrder._meta.get_field("seller"), models.ForeignKey)
        self.assertIsInstance(PurchaseOrderLine._meta.get_field("purchase_order"), models.ForeignKey)
        self.assertIsInstance(PurchaseOrderLine._meta.get_field("listing"), models.ForeignKey)
        self.assertIsInstance(PurchaseOrderLine._meta.get_field("card_variant"), models.ForeignKey)

    def test_listing_quantity_database_constraint_blocks_invalid_save(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            MarketListing.objects.create(
                seller=self.seller,
                inventory_item=self.inventory_item,
                quantity=0,
                quantity_available=0,
                unit_price=Decimal("100.00"),
            )


class ListingServiceTests(TestCase):
    def setUp(self):
        self.seller = get_user_model().objects.create_user(
            username="service-seller",
            password="test-password",
        )
        self.other_user = get_user_model().objects.create_user(
            username="service-other",
            password="test-password",
        )
        game = CardGame.objects.create(name="Pokemon", slug="pokemon-service")
        card_set = CardSet.objects.create(game=game, name="Base Set", code="BASE")
        card = Card.objects.create(game=game, name="Charizard")
        self.variant = CardVariant.objects.create(
            card=card,
            set=card_set,
            collector_number="4/102",
            rarity=CardVariant.Rarity.RARE,
            finish=CardVariant.Finish.HOLO,
        )
        self.inventory_item = InventoryItem.objects.create(
            owner=self.seller,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=5,
            reserved_quantity=0,
        )

    def test_create_listing_reserves_inventory_and_creates_active_listing(self):
        listing = create_listing(
            seller=self.seller,
            inventory_item=self.inventory_item,
            quantity=2,
            unit_price=Decimal("125.50"),
        )
        self.inventory_item.refresh_from_db()

        self.assertEqual(listing.seller, self.seller)
        self.assertEqual(listing.inventory_item, self.inventory_item)
        self.assertEqual(listing.status, MarketListing.Status.ACTIVE)
        self.assertEqual(listing.quantity, 2)
        self.assertEqual(listing.quantity_available, 2)
        self.assertEqual(self.inventory_item.reserved_quantity, 2)
        self.assertEqual(self.inventory_item.available_quantity, 3)

    def test_create_listing_rejects_inventory_owned_by_another_user(self):
        with self.assertRaises(ValidationError):
            create_listing(
                seller=self.other_user,
                inventory_item=self.inventory_item,
                quantity=1,
                unit_price=Decimal("100.00"),
            )

    def test_create_listing_rejects_more_than_available_inventory(self):
        self.inventory_item.reserved_quantity = 4
        self.inventory_item.save(update_fields=("reserved_quantity", "updated_at"))

        with self.assertRaises(ValidationError):
            create_listing(
                seller=self.seller,
                inventory_item=self.inventory_item,
                quantity=2,
                unit_price=Decimal("100.00"),
            )

    def test_create_listing_rejects_invalid_quantity_and_price(self):
        with self.assertRaises(ValidationError):
            create_listing(
                seller=self.seller,
                inventory_item=self.inventory_item,
                quantity=0,
                unit_price=Decimal("100.00"),
            )

        with self.assertRaises(ValidationError):
            create_listing(
                seller=self.seller,
                inventory_item=self.inventory_item,
                quantity=1,
                unit_price=Decimal("-1.00"),
            )

    def test_pause_listing_changes_active_listing_to_paused(self):
        listing = create_listing(
            seller=self.seller,
            inventory_item=self.inventory_item,
            quantity=2,
            unit_price=Decimal("125.50"),
        )

        paused_listing = pause_listing(listing=listing, seller=self.seller)

        self.assertEqual(paused_listing.status, MarketListing.Status.PAUSED)
        self.assertEqual(paused_listing.quantity_available, 2)

    def test_cancel_listing_releases_available_reserved_inventory(self):
        listing = create_listing(
            seller=self.seller,
            inventory_item=self.inventory_item,
            quantity=2,
            unit_price=Decimal("125.50"),
        )

        cancelled_listing = cancel_listing(listing=listing, seller=self.seller)
        self.inventory_item.refresh_from_db()

        self.assertEqual(cancelled_listing.status, MarketListing.Status.CANCELLED)
        self.assertEqual(cancelled_listing.quantity_available, 0)
        self.assertEqual(self.inventory_item.reserved_quantity, 0)
        self.assertEqual(self.inventory_item.available_quantity, 5)

    def test_mark_listing_sold_out_requires_no_available_quantity(self):
        listing = create_listing(
            seller=self.seller,
            inventory_item=self.inventory_item,
            quantity=2,
            unit_price=Decimal("125.50"),
        )

        with self.assertRaises(ValidationError):
            mark_listing_sold_out(listing=listing, seller=self.seller)

        listing.quantity_available = 0
        listing.save(update_fields=("quantity_available", "updated_at"))

        with self.assertRaises(ValidationError):
            mark_listing_sold_out(listing=listing, seller=self.seller)

    def test_listing_transitions_reject_wrong_seller(self):
        listing = create_listing(
            seller=self.seller,
            inventory_item=self.inventory_item,
            quantity=1,
            unit_price=Decimal("100.00"),
        )

        with self.assertRaises(ValidationError):
            pause_listing(listing=listing, seller=self.other_user)
        with self.assertRaises(ValidationError):
            cancel_listing(listing=listing, seller=self.other_user)


class MarketplaceAdminTests(TestCase):
    def test_listing_admin_is_optimized_for_seller_inventory_and_variant_inspection(self):
        listing_admin = admin.site._registry[MarketListing]

        self.assertEqual(
            listing_admin.list_select_related,
            ("seller", "inventory_item__card_variant__card", "inventory_item__card_variant__set"),
        )
        self.assertEqual(listing_admin.autocomplete_fields, ("seller", "inventory_item"))
        self.assertIn("created_at", listing_admin.readonly_fields)
        self.assertIn("updated_at", listing_admin.readonly_fields)

    def test_purchase_order_admin_embeds_read_only_order_lines(self):
        order_admin = admin.site._registry[PurchaseOrder]
        inline = order_admin.inlines[0]

        self.assertEqual(order_admin.list_select_related, ("buyer", "seller"))
        self.assertEqual(order_admin.autocomplete_fields, ("buyer", "seller"))
        self.assertEqual(inline.readonly_fields, ("listing", "card_variant", "quantity", "unit_price"))
        self.assertFalse(inline.can_delete)

    def test_purchase_order_line_admin_is_read_only(self):
        line_admin = admin.site._registry[PurchaseOrderLine]

        self.assertFalse(line_admin.has_add_permission(None))
        self.assertFalse(line_admin.has_delete_permission(None))
        self.assertEqual(
            line_admin.readonly_fields,
            ("purchase_order", "listing", "card_variant", "quantity", "unit_price", "created_at", "updated_at"),
        )


class MarketplaceReadApiTests(APITestCase):
    def setUp(self):
        self.seller = get_user_model().objects.create_user(
            username="api-seller",
            password="test-password",
        )
        self.other_seller = get_user_model().objects.create_user(
            username="api-other-seller",
            password="test-password",
        )
        self.buyer = get_user_model().objects.create_user(
            username="api-buyer",
            password="test-password",
        )
        self.other_buyer = get_user_model().objects.create_user(
            username="api-other-buyer",
            password="test-password",
        )
        game = CardGame.objects.create(name="Pokemon", slug="pokemon-api")
        card_set = CardSet.objects.create(game=game, name="Base Set", code="BASE")
        charizard = Card.objects.create(game=game, name="Charizard")
        blastoise = Card.objects.create(game=game, name="Blastoise")
        self.charizard_variant = CardVariant.objects.create(
            card=charizard,
            set=card_set,
            collector_number="4/102",
            rarity=CardVariant.Rarity.RARE,
            finish=CardVariant.Finish.HOLO,
        )
        self.blastoise_variant = CardVariant.objects.create(
            card=blastoise,
            set=card_set,
            collector_number="2/102",
            rarity=CardVariant.Rarity.RARE,
            finish=CardVariant.Finish.HOLO,
        )
        self.seller_inventory = InventoryItem.objects.create(
            owner=self.seller,
            card_variant=self.charizard_variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=5,
        )
        self.other_seller_inventory = InventoryItem.objects.create(
            owner=self.other_seller,
            card_variant=self.blastoise_variant,
            condition=InventoryItem.Condition.LIGHTLY_PLAYED,
            quantity=3,
        )

    def _create_order(self, *, buyer, seller, listing, total_amount):
        order = PurchaseOrder.objects.create(
            buyer=buyer,
            seller=seller,
            status=PurchaseOrder.Status.COMPLETED,
            total_amount=total_amount,
        )
        PurchaseOrderLine.objects.create(
            purchase_order=order,
            listing=listing,
            card_variant=listing.inventory_item.card_variant,
            quantity=1,
            unit_price=listing.unit_price,
        )
        return order

    def test_listing_list_returns_only_active_available_listings(self):
        active_listing = create_listing(
            seller=self.seller,
            inventory_item=self.seller_inventory,
            quantity=2,
            unit_price=Decimal("125.50"),
        )
        paused_listing = create_listing(
            seller=self.other_seller,
            inventory_item=self.other_seller_inventory,
            quantity=1,
            unit_price=Decimal("60.00"),
        )
        pause_listing(listing=paused_listing, seller=self.other_seller)

        response = self.client.get(reverse("marketplace-listing-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([listing["id"] for listing in response.data], [active_listing.id])
        self.assertEqual(response.data[0]["card_variant"]["card"]["name"], "Charizard")
        self.assertEqual(response.data[0]["condition"], InventoryItem.Condition.NEAR_MINT)

    def test_listing_detail_returns_active_listing(self):
        listing = create_listing(
            seller=self.seller,
            inventory_item=self.seller_inventory,
            quantity=2,
            unit_price=Decimal("125.50"),
        )

        response = self.client.get(reverse("marketplace-listing-detail", kwargs={"pk": listing.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], listing.id)
        self.assertEqual(response.data["seller"]["username"], "api-seller")
        self.assertEqual(response.data["card_variant"]["collector_number"], "4/102")

    def test_listing_detail_hides_non_active_listing(self):
        listing = create_listing(
            seller=self.seller,
            inventory_item=self.seller_inventory,
            quantity=2,
            unit_price=Decimal("125.50"),
        )
        pause_listing(listing=listing, seller=self.seller)

        response = self.client.get(reverse("marketplace-listing-detail", kwargs={"pk": listing.pk}))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_listing_list_filters_by_seller_variant_status_and_price(self):
        charizard_listing = create_listing(
            seller=self.seller,
            inventory_item=self.seller_inventory,
            quantity=2,
            unit_price=Decimal("125.50"),
        )
        create_listing(
            seller=self.other_seller,
            inventory_item=self.other_seller_inventory,
            quantity=1,
            unit_price=Decimal("60.00"),
        )

        seller_response = self.client.get(reverse("marketplace-listing-list"), {"seller": self.seller.id})
        variant_response = self.client.get(
            reverse("marketplace-listing-list"),
            {"card_variant": self.charizard_variant.id},
        )
        price_response = self.client.get(reverse("marketplace-listing-list"), {"price_min": "100", "price_max": "130"})
        status_response = self.client.get(reverse("marketplace-listing-list"), {"status": MarketListing.Status.PAUSED})

        self.assertEqual([listing["id"] for listing in seller_response.data], [charizard_listing.id])
        self.assertEqual([listing["id"] for listing in variant_response.data], [charizard_listing.id])
        self.assertEqual([listing["id"] for listing in price_response.data], [charizard_listing.id])
        self.assertEqual(status_response.data, [])

    def test_sales_history_requires_authentication(self):
        response = self.client.get(reverse("marketplace-my-sales"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_sales_history_returns_only_authenticated_seller_orders(self):
        seller_listing = create_listing(
            seller=self.seller,
            inventory_item=self.seller_inventory,
            quantity=2,
            unit_price=Decimal("125.50"),
        )
        other_listing = create_listing(
            seller=self.other_seller,
            inventory_item=self.other_seller_inventory,
            quantity=1,
            unit_price=Decimal("60.00"),
        )
        own_sale = self._create_order(
            buyer=self.buyer,
            seller=self.seller,
            listing=seller_listing,
            total_amount=Decimal("125.50"),
        )
        self._create_order(
            buyer=self.buyer,
            seller=self.other_seller,
            listing=other_listing,
            total_amount=Decimal("60.00"),
        )
        self.client.force_authenticate(user=self.seller)

        response = self.client.get(reverse("marketplace-my-sales"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([order["id"] for order in response.data], [own_sale.id])
        self.assertEqual(response.data[0]["lines"][0]["card_variant"]["card"]["name"], "Charizard")

    def test_purchase_history_returns_only_authenticated_buyer_orders(self):
        seller_listing = create_listing(
            seller=self.seller,
            inventory_item=self.seller_inventory,
            quantity=2,
            unit_price=Decimal("125.50"),
        )
        own_purchase = self._create_order(
            buyer=self.buyer,
            seller=self.seller,
            listing=seller_listing,
            total_amount=Decimal("125.50"),
        )
        self._create_order(
            buyer=self.other_buyer,
            seller=self.seller,
            listing=seller_listing,
            total_amount=Decimal("125.50"),
        )
        self.client.force_authenticate(user=self.buyer)

        response = self.client.get(reverse("marketplace-my-purchases"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([order["id"] for order in response.data], [own_purchase.id])
        self.assertEqual(response.data[0]["seller"]["username"], "api-seller")


class PurchaseWorkflowTests(TestCase):
    def setUp(self):
        self.seller = get_user_model().objects.create_user(
            username="purchase-seller",
            password="test-password",
        )
        self.buyer = get_user_model().objects.create_user(
            username="purchase-buyer",
            password="test-password",
        )
        self.other_buyer = get_user_model().objects.create_user(
            username="purchase-other-buyer",
            password="test-password",
        )
        game = CardGame.objects.create(name="Pokemon", slug="pokemon-purchase")
        card_set = CardSet.objects.create(game=game, name="Base Set", code="BASE")
        card = Card.objects.create(game=game, name="Charizard")
        self.variant = CardVariant.objects.create(
            card=card,
            set=card_set,
            collector_number="4/102",
            rarity=CardVariant.Rarity.RARE,
            finish=CardVariant.Finish.HOLO,
        )
        self.seller_inventory = InventoryItem.objects.create(
            owner=self.seller,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=5,
        )

    def test_purchase_listing_creates_order_line_updates_listing_and_inventories(self):
        listing = create_listing(
            seller=self.seller,
            inventory_item=self.seller_inventory,
            quantity=3,
            unit_price=Decimal("125.50"),
        )

        order = purchase_listing(buyer=self.buyer, listing=listing, quantity=2)
        listing.refresh_from_db()
        self.seller_inventory.refresh_from_db()
        buyer_inventory = InventoryItem.objects.get(owner=self.buyer, card_variant=self.variant)

        self.assertEqual(order.status, PurchaseOrder.Status.COMPLETED)
        self.assertEqual(order.buyer, self.buyer)
        self.assertEqual(order.seller, self.seller)
        self.assertEqual(order.total_amount, Decimal("251.00"))
        self.assertEqual(order.lines.count(), 1)
        line = order.lines.get()
        self.assertEqual(line.listing, listing)
        self.assertEqual(line.card_variant, self.variant)
        self.assertEqual(line.quantity, 2)
        self.assertEqual(line.unit_price, Decimal("125.50"))
        self.assertEqual(listing.quantity_available, 1)
        self.assertEqual(listing.status, MarketListing.Status.ACTIVE)
        self.assertEqual(self.seller_inventory.quantity, 3)
        self.assertEqual(self.seller_inventory.reserved_quantity, 1)
        self.assertEqual(buyer_inventory.quantity, 2)
        self.assertEqual(buyer_inventory.purchase_price, Decimal("125.50"))
        self.assertTrue(
            self.seller_inventory.history_entries.filter(
                change_type=InventoryHistory.ChangeType.DECREASE,
                quantity_delta=-2,
            ).exists()
        )
        self.assertTrue(
            buyer_inventory.history_entries.filter(
                change_type=InventoryHistory.ChangeType.PURCHASE,
                quantity_delta=2,
            ).exists()
        )

    def test_purchase_listing_records_price_snapshot_for_completed_sale(self):
        listing = create_listing(
            seller=self.seller,
            inventory_item=self.seller_inventory,
            quantity=3,
            unit_price=Decimal("125.50"),
        )

        order = purchase_listing(buyer=self.buyer, listing=listing, quantity=2)
        self.variant.refresh_from_db()

        snapshot = PriceSnapshot.objects.get(card_variant=self.variant)
        self.assertEqual(snapshot.price, Decimal("125.50"))
        self.assertEqual(snapshot.currency, listing.currency)
        self.assertEqual(snapshot.source_name, "marketplace_sale")
        self.assertEqual(snapshot.captured_at, order.created_at)
        self.assertEqual(self.variant.current_value, Decimal("125.50"))

    def test_purchase_listing_can_sell_sellers_final_reserved_quantity(self):
        listing = create_listing(
            seller=self.seller,
            inventory_item=self.seller_inventory,
            quantity=5,
            unit_price=Decimal("100.00"),
        )

        order = purchase_listing(buyer=self.buyer, listing=listing, quantity=5)
        listing.refresh_from_db()
        self.seller_inventory.refresh_from_db()

        self.assertEqual(order.total_amount, Decimal("500.00"))
        self.assertEqual(listing.quantity_available, 0)
        self.assertEqual(listing.status, MarketListing.Status.SOLD_OUT)
        self.assertEqual(self.seller_inventory.quantity, 0)
        self.assertEqual(self.seller_inventory.reserved_quantity, 0)

    def test_purchase_listing_rejects_inactive_listing_without_side_effects(self):
        listing = create_listing(
            seller=self.seller,
            inventory_item=self.seller_inventory,
            quantity=2,
            unit_price=Decimal("100.00"),
        )
        pause_listing(listing=listing, seller=self.seller)

        with self.assertRaises(ValidationError):
            purchase_listing(buyer=self.buyer, listing=listing, quantity=1)

        listing.refresh_from_db()
        self.seller_inventory.refresh_from_db()
        self.assertEqual(PurchaseOrder.objects.count(), 0)
        self.assertEqual(listing.quantity_available, 2)
        self.assertEqual(self.seller_inventory.quantity, 5)
        self.assertEqual(self.seller_inventory.reserved_quantity, 2)

    def test_purchase_listing_rejects_more_than_listing_available_without_side_effects(self):
        listing = create_listing(
            seller=self.seller,
            inventory_item=self.seller_inventory,
            quantity=2,
            unit_price=Decimal("100.00"),
        )

        with self.assertRaises(ValidationError):
            purchase_listing(buyer=self.buyer, listing=listing, quantity=3)

        listing.refresh_from_db()
        self.seller_inventory.refresh_from_db()
        self.assertEqual(PurchaseOrder.objects.count(), 0)
        self.assertEqual(listing.quantity_available, 2)
        self.assertEqual(self.seller_inventory.quantity, 5)
        self.assertEqual(self.seller_inventory.reserved_quantity, 2)

    def test_purchase_listing_rejects_seller_buying_own_listing(self):
        listing = create_listing(
            seller=self.seller,
            inventory_item=self.seller_inventory,
            quantity=1,
            unit_price=Decimal("100.00"),
        )

        with self.assertRaises(ValidationError):
            purchase_listing(buyer=self.seller, listing=listing, quantity=1)

        self.assertEqual(PurchaseOrder.objects.count(), 0)


class BuyEndpointTests(APITestCase):
    def setUp(self):
        self.seller = get_user_model().objects.create_user(
            username="endpoint-seller",
            password="test-password",
        )
        self.buyer = get_user_model().objects.create_user(
            username="endpoint-buyer",
            password="test-password",
        )
        game = CardGame.objects.create(name="Pokemon", slug="pokemon-buy-endpoint")
        card_set = CardSet.objects.create(game=game, name="Base Set", code="BASE")
        card = Card.objects.create(game=game, name="Charizard")
        self.variant = CardVariant.objects.create(
            card=card,
            set=card_set,
            collector_number="4/102",
            rarity=CardVariant.Rarity.RARE,
            finish=CardVariant.Finish.HOLO,
        )
        self.seller_inventory = InventoryItem.objects.create(
            owner=self.seller,
            card_variant=self.variant,
            condition=InventoryItem.Condition.NEAR_MINT,
            quantity=5,
        )

    def test_anonymous_user_cannot_buy_listing(self):
        listing = create_listing(
            seller=self.seller,
            inventory_item=self.seller_inventory,
            quantity=2,
            unit_price=Decimal("125.50"),
        )

        response = self.client.post(
            reverse("marketplace-listing-buy", kwargs={"pk": listing.pk}),
            {"quantity": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_user_can_buy_listing(self):
        listing = create_listing(
            seller=self.seller,
            inventory_item=self.seller_inventory,
            quantity=2,
            unit_price=Decimal("125.50"),
        )
        self.client.force_authenticate(user=self.buyer)

        response = self.client.post(
            reverse("marketplace-listing-buy", kwargs={"pk": listing.pk}),
            {"quantity": 2},
            format="json",
        )
        listing.refresh_from_db()
        self.seller_inventory.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], PurchaseOrder.Status.COMPLETED)
        self.assertEqual(response.data["buyer"]["username"], "endpoint-buyer")
        self.assertEqual(response.data["seller"]["username"], "endpoint-seller")
        self.assertEqual(response.data["total_amount"], "251.00")
        self.assertEqual(response.data["lines"][0]["quantity"], 2)
        self.assertEqual(listing.status, MarketListing.Status.SOLD_OUT)
        self.assertEqual(self.seller_inventory.quantity, 3)
        self.assertEqual(self.seller_inventory.reserved_quantity, 0)

    def test_buy_endpoint_writes_inventory_history_for_successful_purchase(self):
        listing = create_listing(
            seller=self.seller,
            inventory_item=self.seller_inventory,
            quantity=2,
            unit_price=Decimal("125.50"),
        )
        self.client.force_authenticate(user=self.buyer)

        response = self.client.post(
            reverse("marketplace-listing-buy", kwargs={"pk": listing.pk}),
            {"quantity": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        buyer_inventory = InventoryItem.objects.get(owner=self.buyer, card_variant=self.variant)
        seller_history = list(
            self.seller_inventory.history_entries.order_by("created_at", "id").values_list(
                "change_type",
                "quantity_delta",
                "created_by",
            )
        )
        buyer_history = buyer_inventory.history_entries.get()

        self.assertEqual(
            seller_history,
            [
                (InventoryHistory.ChangeType.RESERVE, 2, self.seller.id),
                (InventoryHistory.ChangeType.DECREASE, -1, self.buyer.id),
            ],
        )
        self.assertEqual(buyer_history.change_type, InventoryHistory.ChangeType.PURCHASE)
        self.assertEqual(buyer_history.quantity_delta, 1)
        self.assertEqual(buyer_history.created_by, self.buyer)

    def test_buy_endpoint_rejects_invalid_quantity_shape(self):
        listing = create_listing(
            seller=self.seller,
            inventory_item=self.seller_inventory,
            quantity=2,
            unit_price=Decimal("125.50"),
        )
        self.client.force_authenticate(user=self.buyer)

        response = self.client.post(
            reverse("marketplace-listing-buy", kwargs={"pk": listing.pk}),
            {"quantity": 0},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantity", response.data)

    def test_buy_endpoint_rejects_more_than_available_without_side_effects(self):
        listing = create_listing(
            seller=self.seller,
            inventory_item=self.seller_inventory,
            quantity=2,
            unit_price=Decimal("125.50"),
        )
        self.client.force_authenticate(user=self.buyer)

        response = self.client.post(
            reverse("marketplace-listing-buy", kwargs={"pk": listing.pk}),
            {"quantity": 3},
            format="json",
        )
        listing.refresh_from_db()
        self.seller_inventory.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Cannot purchase more than the available listing quantity.", response.data["detail"])
        self.assertEqual(PurchaseOrder.objects.count(), 0)
        self.assertEqual(listing.quantity_available, 2)
        self.assertEqual(listing.status, MarketListing.Status.ACTIVE)
        self.assertEqual(self.seller_inventory.quantity, 5)
        self.assertEqual(self.seller_inventory.reserved_quantity, 2)
        self.assertFalse(InventoryItem.objects.filter(owner=self.buyer, card_variant=self.variant).exists())
        self.assertEqual(self.seller_inventory.history_entries.count(), 1)

    def test_buy_endpoint_returns_bad_request_for_inactive_listing(self):
        listing = create_listing(
            seller=self.seller,
            inventory_item=self.seller_inventory,
            quantity=2,
            unit_price=Decimal("125.50"),
        )
        pause_listing(listing=listing, seller=self.seller)
        self.client.force_authenticate(user=self.buyer)

        response = self.client.post(
            reverse("marketplace-listing-buy", kwargs={"pk": listing.pk}),
            {"quantity": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Only active listings can be purchased.", response.data["detail"])

    def test_buy_endpoint_returns_bad_request_for_seller_self_purchase(self):
        listing = create_listing(
            seller=self.seller,
            inventory_item=self.seller_inventory,
            quantity=2,
            unit_price=Decimal("125.50"),
        )
        self.client.force_authenticate(user=self.seller)

        response = self.client.post(
            reverse("marketplace-listing-buy", kwargs={"pk": listing.pk}),
            {"quantity": 1},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Seller cannot buy their own listing.", response.data["detail"])
