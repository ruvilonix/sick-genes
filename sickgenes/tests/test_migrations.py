from importlib import import_module
from unittest import skipUnless

from django.apps import apps
from django.db import connection
from django.test import TestCase

migration = import_module('sickgenes.migrations.0002_restore_genefinding_gene_foreign_key')


def gene_foreign_keys():
    """Names of the foreign keys on the gene column of the findings table."""
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, migration.TABLE)
    return [
        name for name, constraint in constraints.items()
        if constraint['foreign_key'] and constraint['columns'] == ['hgnc_gene_id']
    ]


def run_migration():
    with connection.schema_editor() as schema_editor:
        migration.restore_foreign_key(apps, schema_editor)


# Only old Postgres databases can be missing the foreign key
@skipUnless(connection.vendor == 'postgresql', 'Needs Postgres')
class RestoreGeneForeignKeyTests(TestCase):
    def test_adds_the_foreign_key_when_missing(self):
        with connection.cursor() as cursor:
            cursor.execute(f'ALTER TABLE {migration.TABLE} DROP CONSTRAINT {migration.CONSTRAINT}')
        self.assertEqual(gene_foreign_keys(), [])

        run_migration()

        self.assertEqual(gene_foreign_keys(), [migration.CONSTRAINT])

    def test_leaves_an_existing_foreign_key_alone(self):
        self.assertEqual(gene_foreign_keys(), [migration.CONSTRAINT])

        run_migration()

        self.assertEqual(gene_foreign_keys(), [migration.CONSTRAINT])
