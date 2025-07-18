# Generated by Django 5.2.3 on 2025-07-07 14:12

import django.contrib.postgres.fields
import django.contrib.postgres.indexes
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sickgenes', '0028_remove_study_date_added_disease_created_at_and_more'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='hmdbmetabolite',
            name='hmdbmetabolite_iupac_name_idx',
        ),
        migrations.RemoveIndex(
            model_name='hmdbmetabolite',
            name='hmdbmetabolite_tradiupac_idx',
        ),
        migrations.RemoveIndex(
            model_name='hmdbmetabolite',
            name='hmdbmetabolite_synonyms_idx',
        ),
        migrations.RemoveField(
            model_name='hmdbmetabolite',
            name='iupac_name',
        ),
        migrations.RemoveField(
            model_name='hmdbmetabolite',
            name='synonyms',
        ),
        migrations.RemoveField(
            model_name='hmdbmetabolite',
            name='traditional_iupac',
        ),
        migrations.AddField(
            model_name='hmdbmetabolite',
            name='searchable_iupac_name',
            field=models.CharField(default=None, null=True),
        ),
        migrations.AddField(
            model_name='hmdbmetabolite',
            name='searchable_synonyms',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(), default=list, size=None),
        ),
        migrations.AddField(
            model_name='hmdbmetabolite',
            name='searchable_traditional_iupac',
            field=models.CharField(default=None, null=True),
        ),
        migrations.AddIndex(
            model_name='hmdbmetabolite',
            index=models.Index(fields=['searchable_iupac_name'], name='hmdbmetabolite_iupac_name_idx'),
        ),
        migrations.AddIndex(
            model_name='hmdbmetabolite',
            index=models.Index(fields=['searchable_traditional_iupac'], name='hmdbmetabolite_tradiupac_idx'),
        ),
        migrations.AddIndex(
            model_name='hmdbmetabolite',
            index=django.contrib.postgres.indexes.GinIndex(fields=['searchable_synonyms'], name='hmdbmetabolite_synonyms_idx'),
        ),
    ]
