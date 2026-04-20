from decimal import Decimal
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, models, transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

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


class ImportPokemonCardsDatasetCommandTests(TestCase):
    def test_imports_default_sets_repeatably_without_duplicates(self):
        with TemporaryDirectory() as directory:
            csv_path = Path(directory) / "pokemon-cards.csv"
            csv_path.write_text(
                "\n".join(
                    [
                        "id,image_url,caption,name,hp,set_name",
                        (
                            "base1-4,https://example.com/charizard.png,"
                            "\"A Stage 2 Pokemon Card of type Fire with the title Charizard and 120 HP "
                            "of rarity Rare Holo evolved from Charmeleon from the set Base.\","
                            "Charizard,120,Base"
                        ),
                        (
                            "base1-44,https://example.com/bulbasaur.png,"
                            "\"A Basic Pokemon Card of type Grass with the title Bulbasaur and 40 HP "
                            "of rarity Common from the set Base.\","
                            "Bulbasaur,40,Base"
                        ),
                        (
                            "base2-4,https://example.com/jolteon.png,"
                            "\"A Stage 1 Pokemon Card of type Lightning with the title Jolteon and 70 HP "
                            "of rarity Rare Holo evolved from Eevee from the set Jungle.\","
                            "Jolteon,70,Jungle"
                        ),
                    ]
                ),
                encoding="utf-8",
            )
            output = StringIO()

            call_command("import_pokemon_cards_dataset", str(csv_path), stdout=output)
            call_command("import_pokemon_cards_dataset", str(csv_path), stdout=output)

        game = CardGame.objects.get(slug="pokemon")
        base_set = CardSet.objects.get(game=game, code="BASE")
        jungle_set = CardSet.objects.get(game=game, code="JUNGLE")

        self.assertEqual(CardSet.objects.count(), 2)
        self.assertEqual(Card.objects.count(), 3)
        self.assertEqual(CardVariant.objects.count(), 3)
        self.assertEqual(CardImage.objects.count(), 3)

        charizard = Card.objects.get(name="Charizard")
        charizard_variant = CardVariant.objects.get(card=charizard)
        self.assertEqual(charizard.hp, 120)
        self.assertEqual(charizard.card_type, "Pokemon")
        self.assertEqual(charizard.subtype, "Fire")
        self.assertEqual(charizard_variant.set, base_set)
        self.assertEqual(charizard_variant.collector_number, "4/102")
        self.assertEqual(charizard_variant.rarity, CardVariant.Rarity.RARE)
        self.assertEqual(charizard_variant.finish, CardVariant.Finish.HOLO)
        self.assertEqual(charizard_variant.language, "en")
        self.assertEqual(charizard_variant.current_value, Decimal("0.00"))
        self.assertEqual(charizard_variant.image.image_url, "https://example.com/charizard.png")

        jolteon_variant = CardVariant.objects.get(card__name="Jolteon")
        self.assertEqual(jolteon_variant.set, jungle_set)
        self.assertEqual(jolteon_variant.collector_number, "4/64")
        self.assertEqual(jolteon_variant.finish, CardVariant.Finish.HOLO)


class CatalogAdminTests(TestCase):
    def test_card_variant_admin_is_optimized_for_inspection(self):
        variant_admin = admin.site._registry[CardVariant]

        self.assertEqual(variant_admin.list_select_related, ("card", "set"))
        self.assertEqual(variant_admin.autocomplete_fields, ("card", "set"))
        self.assertIn("created_at", variant_admin.readonly_fields)
        self.assertIn("updated_at", variant_admin.readonly_fields)

    def test_card_image_admin_uses_autocomplete_for_variant_lookup(self):
        image_admin = admin.site._registry[CardImage]

        self.assertEqual(image_admin.list_select_related, ("card_variant__card", "card_variant__set"))
        self.assertEqual(image_admin.autocomplete_fields, ("card_variant",))


class CatalogReadApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.game = CardGame.objects.create(name="Pokemon", slug="pokemon")
        cls.card_set = CardSet.objects.create(game=cls.game, name="Base Set", code="BASE")
        cls.dragon = Card.objects.create(
            game=cls.game,
            name="Catalog Dragon",
            card_type="Pokemon",
            subtype="Fire",
            hp=120,
        )
        cls.turtle = Card.objects.create(
            game=cls.game,
            name="Catalog Turtle",
            card_type="Pokemon",
            subtype="Water",
            hp=100,
        )
        dragon_en = CardVariant.objects.create(
            card=cls.dragon,
            set=cls.card_set,
            collector_number="4/102",
            rarity=CardVariant.Rarity.RARE,
            finish=CardVariant.Finish.HOLO,
            language="en",
        )
        dragon_ja = CardVariant.objects.create(
            card=cls.dragon,
            set=cls.card_set,
            collector_number="4/102",
            rarity=CardVariant.Rarity.RARE,
            finish=CardVariant.Finish.HOLO,
            language="ja",
        )
        turtle_en = CardVariant.objects.create(
            card=cls.turtle,
            set=cls.card_set,
            collector_number="2/102",
            rarity=CardVariant.Rarity.RARE,
            finish=CardVariant.Finish.HOLO,
            language="en",
        )
        CardImage.objects.create(
            card_variant=dragon_en,
            image_url="https://example.com/catalog-dragon-en.png",
            image_hash="api-dragon-en",
        )
        CardImage.objects.create(
            card_variant=dragon_ja,
            image_url="https://example.com/catalog-dragon-ja.png",
            image_hash="api-dragon-ja",
        )
        CardImage.objects.create(
            card_variant=turtle_en,
            image_url="https://example.com/catalog-turtle-en.png",
            image_hash="api-turtle-en",
        )

    def test_card_list_returns_stable_card_data(self):
        response = self.client.get(reverse("catalog-card-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["name"], "Catalog Dragon")
        self.assertEqual(response.data["results"][1]["name"], "Catalog Turtle")
        self.assertEqual(response.data["results"][1]["game"]["slug"], "pokemon")

    def test_card_list_paginates_results(self):
        response = self.client.get(reverse("catalog-card-list"), {"page_size": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "Catalog Dragon")
        self.assertIsNotNone(response.data["next"])

    def test_card_detail_returns_variants_for_that_card(self):
        card = Card.objects.get(name="Catalog Dragon")

        response = self.client.get(reverse("catalog-card-detail", kwargs={"pk": card.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Catalog Dragon")
        self.assertEqual(len(response.data["variants"]), 2)
        self.assertEqual(response.data["variants"][0]["collector_number"], "4/102")

    def test_variant_detail_returns_catalog_version_and_image(self):
        variant = CardVariant.objects.get(card__name="Catalog Turtle")

        response = self.client.get(reverse("catalog-variant-detail", kwargs={"pk": variant.pk}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["card"]["name"], "Catalog Turtle")
        self.assertEqual(response.data["set"]["code"], "BASE")
        self.assertEqual(response.data["finish"], CardVariant.Finish.HOLO)
        self.assertEqual(response.data["image"]["image_hash"], "api-turtle-en")

    def test_set_list_returns_sets_with_game_data(self):
        response = self.client.get(reverse("catalog-set-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["code"], "BASE")
        self.assertEqual(response.data[0]["game"]["slug"], "pokemon")

    def test_card_list_filters_by_name_game_set_and_rarity(self):
        name_response = self.client.get(reverse("catalog-card-list"), {"name": "dragon"})
        game_response = self.client.get(reverse("catalog-card-list"), {"game": "pokemon"})
        set_response = self.client.get(reverse("catalog-card-list"), {"set": "BASE"})
        rarity_response = self.client.get(reverse("catalog-card-list"), {"rarity": CardVariant.Rarity.RARE})

        self.assertEqual([card["name"] for card in name_response.data["results"]], ["Catalog Dragon"])
        self.assertEqual(game_response.data["count"], 2)
        self.assertEqual(set_response.data["count"], 2)
        self.assertEqual(rarity_response.data["count"], 2)

    def test_card_list_uses_fixed_query_count_for_fixture_data(self):
        with self.assertNumQueries(2):
            response = self.client.get(reverse("catalog-card-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
