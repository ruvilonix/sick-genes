# Generated by Django 5.2.3 on 2025-07-05 15:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sickgenes', '0022_alter_genefinding_type'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='genefinding',
            constraint=models.CheckConstraint(condition=models.Q(('type__in', ['V', 'A'])), name='sickgenes_genefinding_type_valid'),
        ),
    ]
