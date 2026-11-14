import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Text fields: existing NULLs become '' (Django fills them from the new
    default before adding NOT NULL).

    Gene fields have no default on purpose: if any row is NULL the migration
    fails instead of inventing data. Production had none when this was written.
    """

    dependencies = [
        ('sickgenes', '0073_siteconfiguration_literature_search'),
    ]

    operations = [
        migrations.AlterField(
            model_name='siteconfiguration',
            name='home_page_description',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='siteconfiguration',
            name='about',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='study',
            name='note',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='studycohort',
            name='note',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='hgncgene',
            name='hgnc_id',
            field=models.IntegerField(unique=True),
        ),
        migrations.AlterField(
            model_name='hgncgene',
            name='symbol',
            field=models.CharField(max_length=30),
        ),
        migrations.AlterField(
            model_name='genefinding',
            name='hgnc_gene',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='sickgenes.hgncgene'),
        ),
    ]
