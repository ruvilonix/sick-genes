from django.db import migrations

TABLE = 'sickgenes_genefinding'
# The name Django gives this foreign key in a new database
CONSTRAINT = 'sickgenes_genefindin_hgnc_gene_id_43ace5d4_fk_sickgenes'


def restore_foreign_key(apps, schema_editor):
    """
    Add the foreign key from gene findings to genes where it's missing.

    An early migration (the old 0034) dropped it with raw SQL and it was never
    added back, so databases older than the squashed 0001 don't have it.
    Databases created from the squashed 0001 do, and are left alone.
    """
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, TABLE)
    if any(c['foreign_key'] and c['columns'] == ['hgnc_gene_id'] for c in constraints.values()):
        return

    # Only old Postgres databases get here. This fails, changing nothing, if
    # a finding points at a gene that doesn't exist.
    schema_editor.execute(
        f'ALTER TABLE {TABLE} ADD CONSTRAINT {CONSTRAINT} '
        'FOREIGN KEY (hgnc_gene_id) REFERENCES sickgenes_hgncgene (id) '
        'DEFERRABLE INITIALLY DEFERRED'
    )


class Migration(migrations.Migration):

    dependencies = [
        ('sickgenes', '0001_squashed_0076_remove_metabolites_and_string'),
    ]

    operations = [
        migrations.RunPython(restore_foreign_key, migrations.RunPython.noop),
    ]
