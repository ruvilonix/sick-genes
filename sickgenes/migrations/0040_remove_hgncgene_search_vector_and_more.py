# Generated by Django 5.2.3 on 2025-07-08 19:09

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sickgenes', '0039_hgncgene_search_vector_hmdbmetabolite_search_vector_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='hgncgene',
            name='search_vector',
        ),
        migrations.RemoveField(
            model_name='hmdbmetabolite',
            name='search_vector',
        ),
        migrations.AlterField(
            model_name='metabolitesynonym',
            name='metabolite',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='synonyms', to='sickgenes.hmdbmetabolite'),
        ),
        migrations.AlterField(
            model_name='secondaryaccession',
            name='metabolite',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='secondary_accessions', to='sickgenes.hmdbmetabolite'),
        ),
    ]
