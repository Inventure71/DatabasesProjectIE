import csv
import hashlib
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
        parser.add_argument(
            "--all-source-sets",
            action="store_true",
            help="Import every set_name present in the CSV. Unknown set codes and collector totals are inferred.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        if not csv_path.exists():
            raise CommandError(f"CSV file does not exist: {csv_path}")
        if options["all_source_sets"] and options["source_set_name"]:
            raise CommandError("Choose either --all-source-sets or --source-set-name, not both.")

        rows = self._read_rows(csv_path)
        import_sets = _build_import_set_configs(
            rows=rows,
            selected_source_set_names=options["source_set_name"],
            import_all_source_sets=options["all_source_sets"],
        )

        with transaction.atomic():
            game, _ = CardGame.objects.update_or_create(
                slug="pokemon",
                defaults={
                    "name": "Pokemon",
                    "description": "Pokemon trading card game.",
                },
            )
            card_sets = {
                source_set_name: self._upsert_card_set(
                    game=game,
                    source_set_name=source_set_name,
                    set_config=set_config,
                )
                for source_set_name, set_config in import_sets.items()
            }

            imported_count = 0
            skipped_count = 0

            for row in rows:
                if row["set_name"] not in card_sets:
                    skipped_count += 1
                    continue

                self._import_row(
                    game=game,
                    card_set=card_sets[row["set_name"]],
                    row=row,
                    collector_total=import_sets[row["set_name"]]["collector_total"],
                )
                imported_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {imported_count} card variant(s) from {', '.join(import_sets)}. "
                f"Skipped {skipped_count} row(s)."
            )
        )

    def _read_rows(self, csv_path):
        with csv_path.open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            self._validate_columns(reader.fieldnames)
            return list(reader)

    def _upsert_card_set(self, *, game, source_set_name, set_config):
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
    suffix = _collector_suffix(dataset_id)["value"]
    return f"{suffix}/{collector_total}" if collector_total else str(suffix)


def _collector_suffix(dataset_id):
    match = re.search(r"-([^-]+)$", dataset_id)
    if not match:
        raise CommandError(f"Could not parse collector number from id: {dataset_id}")
    value = match.group(1)
    number_match = re.search(r"\d+", value)
    numeric_value = int(number_match.group(0)) if number_match else None
    return {
        "value": value,
        "numeric_value": numeric_value,
    }


def _build_import_set_configs(*, rows, selected_source_set_names, import_all_source_sets):
    if import_all_source_sets:
        source_set_names = sorted({row["set_name"] for row in rows if row["set_name"]})
    else:
        source_set_names = selected_source_set_names or list(DEFAULT_IMPORT_SETS)

    inferred_totals = _infer_collector_totals(rows)
    generated_codes = _generate_set_codes(source_set_names)
    import_sets = {}
    for source_set_name in source_set_names:
        default_config = DEFAULT_IMPORT_SETS.get(source_set_name)
        import_sets[source_set_name] = {
            "set_name": default_config["set_name"] if default_config else source_set_name,
            "set_code": default_config["set_code"] if default_config else generated_codes[source_set_name],
            "collector_total": (
                default_config["collector_total"]
                if default_config
                else inferred_totals.get(source_set_name)
            ),
        }
    return import_sets


def _infer_collector_totals(rows):
    totals = {}
    for row in rows:
        source_set_name = row["set_name"]
        numeric_value = _collector_suffix(row["id"])["numeric_value"]
        if numeric_value is None:
            continue
        totals[source_set_name] = max(totals.get(source_set_name, numeric_value), numeric_value)
    return totals


def _generate_set_codes(source_set_names):
    used_codes = {}
    generated_codes = {}
    for source_set_name in sorted(source_set_names):
        base_code = _normalize_set_code(source_set_name)
        set_code = base_code
        if set_code in used_codes and used_codes[set_code] != source_set_name:
            digest = hashlib.sha1(source_set_name.encode("utf-8")).hexdigest()[:6].upper()
            set_code = f"{base_code[:33]}_{digest}"
        used_codes[set_code] = source_set_name
        generated_codes[source_set_name] = set_code
    return generated_codes


def _normalize_set_code(source_set_name):
    code = re.sub(r"[^A-Za-z0-9]+", "_", source_set_name).strip("_").upper()
    return (code or "SET")[:40]


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
