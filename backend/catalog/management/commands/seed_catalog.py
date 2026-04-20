from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from catalog.models import Card, CardGame, CardImage, CardSet, CardVariant


class Command(BaseCommand):
    help = "Seed the database with a small coherent catalog dataset."

    def handle(self, *args, **options):
        game, _ = CardGame.objects.update_or_create(
            slug="pokemon",
            defaults={
                "name": "Pokemon",
                "description": "Pokemon trading card game.",
            },
        )
        card_set, _ = CardSet.objects.update_or_create(
            game=game,
            code="BASE",
            defaults={
                "name": "Base Set",
                "release_date": date(1999, 1, 9),
                "description": "Original English Pokemon TCG base set.",
            },
        )

        charizard = self._upsert_card(
            game=game,
            name="Charizard",
            card_type="Pokemon",
            subtype="Fire",
            description="Spits fire that is hot enough to melt boulders.",
            artist_name="Mitsuhiro Arita",
            hp=120,
        )
        blastoise = self._upsert_card(
            game=game,
            name="Blastoise",
            card_type="Pokemon",
            subtype="Water",
            description="A brutal Pokemon with pressurized water jets on its shell.",
            artist_name="Mitsuhiro Arita",
            hp=100,
        )

        self._upsert_variant_with_image(
            card=charizard,
            card_set=card_set,
            collector_number="4/102",
            rarity=CardVariant.Rarity.RARE,
            finish=CardVariant.Finish.HOLO,
            language="en",
            current_value=Decimal("350.00"),
            image_url="https://example.com/cards/base-set-charizard-holo-en.png",
            image_hash="seed-charizard-holo-en",
        )
        self._upsert_variant_with_image(
            card=charizard,
            card_set=card_set,
            collector_number="4/102",
            rarity=CardVariant.Rarity.RARE,
            finish=CardVariant.Finish.HOLO,
            language="ja",
            current_value=Decimal("700.00"),
            image_url="https://example.com/cards/base-set-charizard-holo-ja.png",
            image_hash="seed-charizard-holo-ja",
        )
        self._upsert_variant_with_image(
            card=blastoise,
            card_set=card_set,
            collector_number="2/102",
            rarity=CardVariant.Rarity.RARE,
            finish=CardVariant.Finish.HOLO,
            language="en",
            current_value=Decimal("180.00"),
            image_url="https://example.com/cards/base-set-blastoise-holo-en.png",
            image_hash="seed-blastoise-holo-en",
        )

        self.stdout.write(self.style.SUCCESS("Catalog seed data loaded."))

    def _upsert_card(self, **fields):
        card, _ = Card.objects.update_or_create(
            game=fields["game"],
            name=fields["name"],
            defaults={
                "card_type": fields.get("card_type", ""),
                "subtype": fields.get("subtype", ""),
                "description": fields.get("description", ""),
                "artist_name": fields.get("artist_name", ""),
                "attack": fields.get("attack"),
                "defense": fields.get("defense"),
                "hp": fields.get("hp"),
            },
        )
        return card

    def _upsert_variant_with_image(
        self,
        *,
        card,
        card_set,
        collector_number,
        rarity,
        finish,
        language,
        current_value,
        image_url,
        image_hash,
    ):
        variant, _ = CardVariant.objects.update_or_create(
            card=card,
            set=card_set,
            collector_number=collector_number,
            finish=finish,
            language=language,
            edition_label="",
            is_first_edition=False,
            defaults={
                "rarity": rarity,
                "current_value": current_value,
            },
        )
        CardImage.objects.update_or_create(
            card_variant=variant,
            defaults={
                "image_url": image_url,
                "image_hash": image_hash,
                "width": 734,
                "height": 1024,
            },
        )
        return variant
