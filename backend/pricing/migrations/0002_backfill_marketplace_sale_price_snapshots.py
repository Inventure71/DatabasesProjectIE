from django.db import migrations


MARKETPLACE_SALE_SOURCE = "marketplace_sale"


def backfill_marketplace_sale_snapshots(apps, schema_editor):
    PurchaseOrderLine = apps.get_model("marketplace", "PurchaseOrderLine")
    PriceSnapshot = apps.get_model("pricing", "PriceSnapshot")
    CardVariant = apps.get_model("catalog", "CardVariant")

    completed_lines = (
        PurchaseOrderLine.objects.filter(purchase_order__status="COMPLETED")
        .select_related("purchase_order")
        .order_by("purchase_order__created_at", "id")
    )
    touched_variant_ids = set()

    for line in completed_lines.iterator():
        captured_at = line.purchase_order.created_at
        snapshot_exists = PriceSnapshot.objects.filter(
            card_variant_id=line.card_variant_id,
            price=line.unit_price,
            source_name=MARKETPLACE_SALE_SOURCE,
            captured_at=captured_at,
        ).exists()
        if snapshot_exists:
            continue

        PriceSnapshot.objects.create(
            card_variant_id=line.card_variant_id,
            price=line.unit_price,
            currency=line.purchase_order.currency,
            source_name=MARKETPLACE_SALE_SOURCE,
            captured_at=captured_at,
        )
        touched_variant_ids.add(line.card_variant_id)

    for variant_id in touched_variant_ids:
        latest_snapshot = (
            PriceSnapshot.objects.filter(card_variant_id=variant_id)
            .order_by("-captured_at", "-id")
            .first()
        )
        if latest_snapshot is not None:
            CardVariant.objects.filter(pk=variant_id).update(current_value=latest_snapshot.price)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("marketplace", "0001_initial"),
        ("pricing", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(backfill_marketplace_sale_snapshots, noop_reverse),
    ]
