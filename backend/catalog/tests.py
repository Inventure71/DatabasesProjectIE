from decimal import Decimal
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, models, transaction
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.test import TestCase

from catalog.models import Card, CardGame, CardImage, CardSet, CardVariant


class CatalogModelTests(TestCase):
    def test_variant_connects_card_to_set(self):
        game = CardGame.objects.create(name="Pokemon", slug="pokemon")
        card_set = CardSet.objects.create(game=game, name="Base Set", code="BASE")
        card = Card.objects.create(
            game=game,
            name="Charizard",
            card_type="Pokemon",
            subtype="Fire",
            hp=120,
        )

        variant = CardVariant.objects.create(
            card=card,
            set=card_set,
            collector_number="4/102",
            rarity=CardVariant.Rarity.RARE,
            finish=CardVariant.Finish.HOLO,
            language="en",
            current_value=Decimal("350.00"),
        )

        self.assertEqual(variant.card, card)
        self.assertEqual(variant.set, card_set)
        self.assertIn(variant, card.variants.all())
        self.assertIn(variant, card_set.variants.all())

    def test_card_image_belongs_to_variant(self):
        game = CardGame.objects.create(name="Pokemon", slug="pokemon")
        card_set = CardSet.objects.create(game=game, name="Base Set", code="BASE")
        card = Card.objects.create(game=game, name="Charizard")
        variant = CardVariant.objects.create(card=card, set=card_set)

        image = CardImage.objects.create(
            card_variant=variant,
            image_url="https://example.com/charizard.png",
            image_hash="abc123",
            width=734,
            height=1024,
        )

        self.assertEqual(image.card_variant, variant)
        self.assertEqual(variant.image, image)

    def test_variant_can_have_only_one_image(self):
        game = CardGame.objects.create(name="Pokemon", slug="pokemon")
        card_set = CardSet.objects.create(game=game, name="Base Set", code="BASE")
        card = Card.objects.create(game=game, name="Charizard")
        variant = CardVariant.objects.create(card=card, set=card_set)

        CardImage.objects.create(
            card_variant=variant,
            image_url="https://example.com/front.png",
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            CardImage.objects.create(
                card_variant=variant,
                image_url="https://example.com/duplicate.png",
            )

    def test_card_set_code_is_unique_per_game(self):
        game = CardGame.objects.create(name="Pokemon", slug="pokemon")
        CardSet.objects.create(game=game, name="Base Set", code="BASE")

        with self.assertRaises(IntegrityError), transaction.atomic():
            CardSet.objects.create(game=game, name="Base Set Duplicate", code="BASE")

    def test_variant_current_value_cannot_be_negative(self):
        game = CardGame.objects.create(name="Pokemon", slug="pokemon")
        card_set = CardSet.objects.create(game=game, name="Base Set", code="BASE")
        card = Card.objects.create(game=game, name="Charizard")

        variant = CardVariant(
            card=card,
            set=card_set,
            current_value=Decimal("-1.00"),
        )

        with self.assertRaises(ValidationError):
            variant.full_clean()

    def test_catalog_foreign_key_shape_is_explicit(self):
        self.assertIsInstance(CardSet._meta.get_field("game"), models.ForeignKey)
        self.assertIsInstance(Card._meta.get_field("game"), models.ForeignKey)
        self.assertIsInstance(CardVariant._meta.get_field("card"), models.ForeignKey)
        self.assertIsInstance(CardVariant._meta.get_field("set"), models.ForeignKey)
        self.assertIsInstance(CardImage._meta.get_field("card_variant"), models.OneToOneField)


class SeedCatalogCommandTests(TestCase):
    def test_seed_catalog_creates_valid_repeatable_sample_data(self):
        output = StringIO()

        call_command("seed_catalog", stdout=output)
        call_command("seed_catalog", stdout=output)

        game = CardGame.objects.get(slug="pokemon")
        card_set = CardSet.objects.get(game=game, code="BASE")
        charizard = Card.objects.get(game=game, name="Charizard")
        blastoise = Card.objects.get(game=game, name="Blastoise")

        self.assertEqual(CardGame.objects.count(), 1)
        self.assertEqual(CardSet.objects.count(), 1)
        self.assertEqual(Card.objects.count(), 2)
        self.assertEqual(CardVariant.objects.count(), 3)
        self.assertEqual(CardImage.objects.count(), 3)

        self.assertEqual(card_set.game, game)
        self.assertEqual(charizard.game, game)
        self.assertEqual(blastoise.game, game)

        for variant in CardVariant.objects.all():
            self.assertEqual(variant.set, card_set)
            self.assertEqual(variant.card.game, game)
            self.assertIsNotNone(variant.image)


class CatalogReadApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_catalog", stdout=StringIO())

    def test_card_list_returns_stable_card_data(self):
        response = self.client.get(reverse("catalog-card-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["name"], "Blastoise")
        self.assertEqual(response.data[1]["name"], "Charizard")
        self.assertEqual(response.data[1]["game"]["slug"], "pokemon")

    def test_card_detail_returns_variants_for_that_card(self):
        charizard = Card.objects.get(name="Charizard")

        response = self.client.get(reverse("catalog-card-detail", kwargs={"pk": charizard.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Charizard")
        self.assertEqual(len(response.data["variants"]), 2)
        self.assertEqual(response.data["variants"][0]["collector_number"], "4/102")

    def test_variant_detail_returns_catalog_version_and_image(self):
        variant = CardVariant.objects.get(card__name="Blastoise")

        response = self.client.get(reverse("catalog-variant-detail", kwargs={"pk": variant.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["card"]["name"], "Blastoise")
        self.assertEqual(response.data["set"]["code"], "BASE")
        self.assertEqual(response.data["finish"], CardVariant.Finish.HOLO)
        self.assertEqual(response.data["image"]["image_hash"], "seed-blastoise-holo-en")

    def test_set_list_returns_sets_with_game_data(self):
        response = self.client.get(reverse("catalog-set-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["code"], "BASE")
        self.assertEqual(response.data[0]["game"]["slug"], "pokemon")

    def test_card_list_filters_by_name_game_set_and_rarity(self):
        name_response = self.client.get(reverse("catalog-card-list"), {"name": "zard"})
        game_response = self.client.get(reverse("catalog-card-list"), {"game": "pokemon"})
        set_response = self.client.get(reverse("catalog-card-list"), {"set": "BASE"})
        rarity_response = self.client.get(reverse("catalog-card-list"), {"rarity": CardVariant.Rarity.RARE})

        self.assertEqual([card["name"] for card in name_response.data], ["Charizard"])
        self.assertEqual(len(game_response.data), 2)
        self.assertEqual(len(set_response.data), 2)
        self.assertEqual(len(rarity_response.data), 2)

    def test_card_list_uses_fixed_query_count_for_seeded_data(self):
        with self.assertNumQueries(1):
            response = self.client.get(reverse("catalog-card-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
