from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations


MARKETPLACE_SALE_SOURCE = "marketplace_sale"
RECENT_SALE_LIMIT = 100
MONEY_QUANTUM = Decimal("0.01")


def recalculate_current_values(apps, schema_editor):
    CardVariant = apps.get_model("catalog", "CardVariant")
    PriceSnapshot = apps.get_model("pricing", "PriceSnapshot")

    variant_ids = (
        PriceSnapshot.objects.filter(source_name=MARKETPLACE_SALE_SOURCE)
        .order_by()
        .values_list("card_variant_id", flat=True)
        .distinct()
    )

    for variant_id in variant_ids:
        prices = list(
            PriceSnapshot.objects.filter(
                card_variant_id=variant_id,
                source_name=MARKETPLACE_SALE_SOURCE,
            )
            .order_by("-captured_at", "-id")
            .values_list("price", flat=True)[:RECENT_SALE_LIMIT]
        )
        if not prices:
            continue

        average_price = sum(prices, Decimal("0.00")) / Decimal(len(prices))
        current_value = average_price.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
        CardVariant.objects.filter(pk=variant_id).update(current_value=current_value)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("pricing", "0002_backfill_marketplace_sale_price_snapshots"),
    ]

    operations = [
        migrations.RunPython(recalculate_current_values, noop_reverse),
    ]
