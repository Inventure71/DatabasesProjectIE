import csv
import re
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import Card, CardGame, CardImage, CardSet, CardVariant


DEFAULT_CSV_PATH = "original_datasets/pokemon-cards/pokemon-cards.csv"
DEFAULT_IMPORT_SETS = {
    "Base": {
        "set_name": "Base Set",
        "set_code": "BASE",
        "collector_total": 102,
    },
    "Jungle": {
        "set_name": "Jungle",
        "set_code": "JUNGLE",
        "collector_total": 64,
    },
}


class Command(BaseCommand):
    help = "Import ownable Pokemon card variants from the downloaded pokemon-cards CSV."

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            nargs="?",
            default=DEFAULT_CSV_PATH,
            help=f"Path to pokemon-cards.csv. Defaults to {DEFAULT_CSV_PATH}.",
        )
        parser.add_argument(
            "--source-set-name",
            action="append",
            choices=sorted(DEFAULT_IMPORT_SETS),
            help="Dataset set_name value to import. Can be passed more than once. Defaults to Base and Jungle.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        if not csv_path.exists():
            raise CommandError(f"CSV file does not exist: {csv_path}")

        selected_source_set_names = options["source_set_name"] or list(DEFAULT_IMPORT_SETS)

        with transaction.atomic():
            game, _ = CardGame.objects.update_or_create(
                slug="pokemon",
                defaults={
                    "name": "Pokemon",
                    "description": "Pokemon trading card game.",
                },
            )
            card_sets = {
                source_set_name: self._upsert_card_set(game=game, source_set_name=source_set_name)
                for source_set_name in selected_source_set_names
            }

            imported_count = 0
            skipped_count = 0

            with csv_path.open(newline="", encoding="utf-8") as csv_file:
                reader = csv.DictReader(csv_file)
                self._validate_columns(reader.fieldnames)

                for row in reader:
                    if row["set_name"] not in card_sets:
                        skipped_count += 1
                        continue

                    self._import_row(
                        game=game,
                        card_set=card_sets[row["set_name"]],
                        row=row,
                        collector_total=DEFAULT_IMPORT_SETS[row["set_name"]]["collector_total"],
                    )
                    imported_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {imported_count} card variant(s) from {', '.join(selected_source_set_names)}. "
                f"Skipped {skipped_count} row(s)."
            )
        )

    def _upsert_card_set(self, *, game, source_set_name):
        set_config = DEFAULT_IMPORT_SETS[source_set_name]
        card_set, _ = CardSet.objects.update_or_create(
            game=game,
            code=set_config["set_code"],
            defaults={
                "name": set_config["set_name"],
                "description": f"Imported Pokemon TCG {set_config['set_name']} cards.",
            },
        )
        return card_set

    def _validate_columns(self, fieldnames):
        required_columns = {"id", "image_url", "caption", "name", "hp", "set_name"}
        missing_columns = required_columns - set(fieldnames or [])
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise CommandError(f"CSV is missing required column(s): {missing}")

    def _import_row(self, *, game, card_set, row, collector_total):
        metadata = _parse_caption(row["caption"])
        card, _ = Card.objects.update_or_create(
            game=game,
            name=row["name"],
            defaults={
                "card_type": "Pokemon",
                "subtype": metadata["subtype"],
                "description": row["caption"],
                "hp": _parse_int(row["hp"]),
            },
        )
        variant, _ = CardVariant.objects.update_or_create(
            card=card,
            set=card_set,
            collector_number=_collector_number(row["id"], collector_total=collector_total),
            finish=metadata["finish"],
            language="en",
            edition_label="",
            is_first_edition=False,
            defaults={
                "rarity": metadata["rarity"],
                "current_value": Decimal("0.00"),
            },
        )
        CardImage.objects.update_or_create(
            card_variant=variant,
            defaults={
                "image_url": row["image_url"],
                "image_hash": "",
                "width": None,
                "height": None,
            },
        )


def _collector_number(dataset_id, *, collector_total):
    match = re.search(r"-(\d+)$", dataset_id)
    if not match:
        raise CommandError(f"Could not parse collector number from id: {dataset_id}")
    return f"{int(match.group(1))}/{collector_total}"


def _parse_caption(caption):
    rarity_text = _match_text(caption, r"rarity (.+?) from the set")
    subtype = _match_text(caption, r"of type (.+?) with the title")
    return {
        "rarity": _map_rarity(rarity_text),
        "finish": CardVariant.Finish.HOLO if "Holo" in rarity_text else CardVariant.Finish.NORMAL,
        "subtype": subtype,
    }


def _match_text(value, pattern):
    match = re.search(pattern, value)
    return match.group(1).strip() if match else ""


def _map_rarity(rarity_text):
    normalized = rarity_text.lower()
    if "secret" in normalized:
        return CardVariant.Rarity.SECRET_RARE
    if "rare" in normalized:
        return CardVariant.Rarity.RARE
    if "uncommon" in normalized:
        return CardVariant.Rarity.UNCOMMON
    if "common" in normalized:
        return CardVariant.Rarity.COMMON
    if "promo" in normalized:
        return CardVariant.Rarity.PROMO
    return CardVariant.Rarity.COMMON


def _parse_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
