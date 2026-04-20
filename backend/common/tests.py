from django.db import connection, models
from django.test import TransactionTestCase

from common.models import TimeStampedModel


class TimestampProbe(TimeStampedModel):
    name = models.CharField(max_length=50)

    class Meta:
        app_label = "common"


class TimeStampedModelTests(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        table_name = TimestampProbe._meta.db_table

        with connection.schema_editor() as schema_editor:
            if table_name in connection.introspection.table_names():
                schema_editor.delete_model(TimestampProbe)
            schema_editor.create_model(TimestampProbe)

    @classmethod
    def tearDownClass(cls):
        table_name = TimestampProbe._meta.db_table

        with connection.schema_editor() as schema_editor:
            if table_name in connection.introspection.table_names():
                schema_editor.delete_model(TimestampProbe)

        super().tearDownClass()

    def test_sets_created_at_and_updated_at_on_create(self):
        probe = TimestampProbe.objects.create(name="example")

        self.assertIsNotNone(probe.created_at)
        self.assertIsNotNone(probe.updated_at)

    def test_updates_updated_at_when_saved_again(self):
        probe = TimestampProbe.objects.create(name="before")
        original_updated_at = probe.updated_at

        probe.name = "after"
        probe.save()
        probe.refresh_from_db()

        self.assertGreater(probe.updated_at, original_updated_at)
