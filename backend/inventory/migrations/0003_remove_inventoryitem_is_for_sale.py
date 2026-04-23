from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("inventory", "0002_remove_inventoryitem_inventory_quantity_positive_and_more"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="inventoryitem",
            name="inventory_owner_sale_idx",
        ),
        migrations.RemoveField(
            model_name="inventoryitem",
            name="is_for_sale",
        ),
    ]
