import csv
import hashlib
import re
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

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
        import_rows, skipped_count = _prepare_import_rows(rows=rows, import_sets=import_sets)

        with transaction.atomic():
            game, _ = CardGame.objects.update_or_create(
                slug="pokemon",
                defaults={
                    "name": "Pokemon",
                    "description": "Pokemon trading card game.",
                },
            )
            card_sets = self._bulk_upsert_card_sets(game=game, import_sets=import_sets)
            cards = self._bulk_upsert_cards(game=game, import_rows=import_rows)
            variants = self._bulk_upsert_variants(
                cards=cards,
                card_sets=card_sets,
                import_rows=import_rows,
            )
            self._bulk_upsert_images(variants=variants, import_rows=import_rows)

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(import_rows)} card variant(s) from {', '.join(import_sets)}. "
                f"Skipped {skipped_count} row(s)."
            )
        )

    def _read_rows(self, csv_path):
        with csv_path.open(newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            self._validate_columns(reader.fieldnames)
            return list(reader)

    def _validate_columns(self, fieldnames):
        required_columns = {"id", "image_url", "caption", "name", "hp", "set_name"}
        missing_columns = required_columns - set(fieldnames or [])
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise CommandError(f"CSV is missing required column(s): {missing}")

    def _bulk_upsert_card_sets(self, *, game, import_sets):
        now = timezone.now()
        set_codes = [set_config["set_code"] for set_config in import_sets.values()]
        existing_by_code = {
            card_set.code: card_set
            for card_set in CardSet.objects.filter(game=game, code__in=set_codes)
        }

        card_sets_to_create = []
        card_sets_to_update = []
        for set_config in import_sets.values():
            defaults = {
                "name": set_config["set_name"],
                "description": f"Imported Pokemon TCG {set_config['set_name']} cards.",
            }
            card_set = existing_by_code.get(set_config["set_code"])
            if card_set:
                card_set.name = defaults["name"]
                card_set.description = defaults["description"]
                card_set.updated_at = now
                card_sets_to_update.append(card_set)
            else:
                card_sets_to_create.append(
                    CardSet(
                        game=game,
                        code=set_config["set_code"],
                        **defaults,
                    )
                )

        if card_sets_to_create:
            CardSet.objects.bulk_create(card_sets_to_create, batch_size=1000)
        if card_sets_to_update:
            CardSet.objects.bulk_update(
                card_sets_to_update,
                ["name", "description", "updated_at"],
                batch_size=1000,
            )

        card_sets_by_code = {
            card_set.code: card_set
            for card_set in CardSet.objects.filter(game=game, code__in=set_codes)
        }
        return {
            source_set_name: card_sets_by_code[set_config["set_code"]]
            for source_set_name, set_config in import_sets.items()
        }

    def _bulk_upsert_cards(self, *, game, import_rows):
        latest_by_name = {}
        for import_row in import_rows:
            latest_by_name[import_row["name"]] = import_row

        names = list(latest_by_name)
        existing_by_name = {
            card.name: card
            for card in Card.objects.filter(game=game, name__in=names)
        }
        cards_to_create = []
        for name, import_row in latest_by_name.items():
            if name in existing_by_name:
                continue
            cards_to_create.append(
                Card(
                    game=game,
                    name=name,
                    card_type="Pokemon",
                    subtype=import_row["subtype"],
                    description=import_row["caption"],
                    hp=import_row["hp"],
                )
            )

        if cards_to_create:
            Card.objects.bulk_create(cards_to_create, batch_size=1000)

        cards_by_name = {
            card.name: card
            for card in Card.objects.filter(game=game, name__in=names)
        }
        now = timezone.now()
        cards_to_update = []
        for name, import_row in latest_by_name.items():
            card = cards_by_name[name]
            card.card_type = "Pokemon"
            card.subtype = import_row["subtype"]
            card.description = import_row["caption"]
            card.hp = import_row["hp"]
            card.updated_at = now
            cards_to_update.append(card)

        if cards_to_update:
            Card.objects.bulk_update(
                cards_to_update,
                ["card_type", "subtype", "description", "hp", "updated_at"],
                batch_size=1000,
            )
        return cards_by_name

    def _bulk_upsert_variants(self, *, cards, card_sets, import_rows):
        existing_variants = CardVariant.objects.filter(
            card_id__in=[card.id for card in cards.values()],
            set_id__in=[card_set.id for card_set in card_sets.values()],
        )
        existing_by_key = {
            _variant_key_from_object(variant): variant
            for variant in existing_variants
        }

        desired_by_key = {}
        for import_row in import_rows:
            card = cards[import_row["name"]]
            card_set = card_sets[import_row["source_set_name"]]
            key = _variant_key(
                card_id=card.id,
                set_id=card_set.id,
                collector_number=import_row["collector_number"],
                finish=import_row["finish"],
                language="en",
                edition_label="",
                is_first_edition=False,
            )
            import_row["variant_key"] = key
            desired_by_key[key] = {
                "card": card,
                "card_set": card_set,
                "import_row": import_row,
            }

        variants_to_create = []
        variants_to_update = []
        now = timezone.now()
        for key, desired in desired_by_key.items():
            import_row = desired["import_row"]
            variant = existing_by_key.get(key)
            if variant:
                variant.rarity = import_row["rarity"]
                variant.current_value = Decimal("0.00")
                variant.updated_at = now
                variants_to_update.append(variant)
            else:
                variants_to_create.append(
                    CardVariant(
                        card=desired["card"],
                        set=desired["card_set"],
                        collector_number=import_row["collector_number"],
                        rarity=import_row["rarity"],
                        finish=import_row["finish"],
                        language="en",
                        edition_label="",
                        is_first_edition=False,
                        current_value=Decimal("0.00"),
                    )
                )

        if variants_to_create:
            CardVariant.objects.bulk_create(variants_to_create, batch_size=1000)
        if variants_to_update:
            CardVariant.objects.bulk_update(
                variants_to_update,
                ["rarity", "current_value", "updated_at"],
                batch_size=1000,
            )

        all_variants = CardVariant.objects.filter(
            card_id__in=[card.id for card in cards.values()],
            set_id__in=[card_set.id for card_set in card_sets.values()],
        )
        return {
            _variant_key_from_object(variant): variant
            for variant in all_variants
        }

    def _bulk_upsert_images(self, *, variants, import_rows):
        desired_by_variant_id = {}
        for import_row in import_rows:
            variant = variants[import_row["variant_key"]]
            desired_by_variant_id[variant.id] = {
                "variant": variant,
                "image_url": import_row["image_url"],
            }

        existing_images_by_variant_id = {
            image.card_variant_id: image
            for image in CardImage.objects.filter(card_variant_id__in=desired_by_variant_id)
        }

        images_to_create = []
        images_to_update = []
        now = timezone.now()
        for variant_id, desired in desired_by_variant_id.items():
            image = existing_images_by_variant_id.get(variant_id)
            if image:
                image.image_url = desired["image_url"]
                image.image_hash = ""
                image.width = None
                image.height = None
                image.updated_at = now
                images_to_update.append(image)
            else:
                images_to_create.append(
                    CardImage(
                        card_variant=desired["variant"],
                        image_url=desired["image_url"],
                        image_hash="",
                        width=None,
                        height=None,
                    )
                )

        if images_to_create:
            CardImage.objects.bulk_create(images_to_create, batch_size=1000)
        if images_to_update:
            CardImage.objects.bulk_update(
                images_to_update,
                ["image_url", "image_hash", "width", "height", "updated_at"],
                batch_size=1000,
            )


def _prepare_import_rows(*, rows, import_sets):
    import_rows = []
    skipped_count = 0
    for row in rows:
        source_set_name = row["set_name"]
        if source_set_name not in import_sets:
            skipped_count += 1
            continue

        metadata = _parse_caption(row["caption"])
        collector_number = _collector_number(
            row["id"],
            collector_total=import_sets[source_set_name]["collector_total"],
        )
        import_row = {
            "source_set_name": source_set_name,
            "name": row["name"],
            "caption": row["caption"],
            "hp": _parse_int(row["hp"]),
            "image_url": row["image_url"],
            "collector_number": collector_number,
            "rarity": metadata["rarity"],
            "finish": metadata["finish"],
            "subtype": metadata["subtype"],
        }
        import_rows.append(import_row)
    return import_rows, skipped_count


def _variant_key_from_object(variant):
    return _variant_key(
        card_id=variant.card_id,
        set_id=variant.set_id,
        collector_number=variant.collector_number,
        finish=variant.finish,
        language=variant.language,
        edition_label=variant.edition_label,
        is_first_edition=variant.is_first_edition,
    )


def _variant_key(*, card_id, set_id, collector_number, finish, language, edition_label, is_first_edition):
    return (
        card_id,
        set_id,
        collector_number,
        finish,
        language,
        edition_label,
        is_first_edition,
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
