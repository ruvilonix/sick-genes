# Generated by Django 5.2.4 on 2025-07-12 14:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sickgenes', '0049_genefinding_unique_study_gene'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='disease',
            options={'ordering': ['name']},
        ),
        migrations.RemoveField(
            model_name='studycohort',
            name='control_tags',
        ),
    ]
