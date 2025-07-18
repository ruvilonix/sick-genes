# Generated by Django 5.2.4 on 2025-07-12 19:23

import django.db.models.functions.text
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sickgenes', '0050_alter_disease_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studycohort',
            name='disease_tags',
            field=models.ManyToManyField(related_name='study_cohorts', to='sickgenes.disease'),
        ),
        migrations.AddIndex(
            model_name='hmdbmetabolite',
            index=models.Index(django.db.models.functions.text.Upper('accession'), name='metab_accession_idx'),
        ),
        migrations.AddIndex(
            model_name='hmdbmetabolite',
            index=models.Index(django.db.models.functions.text.Upper('name'), name='metab_name_idx'),
        ),
        migrations.AddIndex(
            model_name='hmdbmetabolite',
            index=models.Index(django.db.models.functions.text.Upper('cas_registry_number'), name='metab_cas_registry_idx'),
        ),
        migrations.AddIndex(
            model_name='hmdbmetabolite',
            index=models.Index(django.db.models.functions.text.Upper('drugbank_id'), name='metab_drugbank_id_idx'),
        ),
        migrations.AddIndex(
            model_name='hmdbmetabolite',
            index=models.Index(django.db.models.functions.text.Upper('foodb_id'), name='metab_foodb_id_idx'),
        ),
        migrations.AddIndex(
            model_name='hmdbmetabolite',
            index=models.Index(django.db.models.functions.text.Upper('knapsack_id'), name='metab_knapsack_id_idx'),
        ),
        migrations.AddIndex(
            model_name='hmdbmetabolite',
            index=models.Index(django.db.models.functions.text.Upper('biocyc_id'), name='metab_biocyc_id_idx'),
        ),
        migrations.AddIndex(
            model_name='hmdbmetabolite',
            index=models.Index(django.db.models.functions.text.Upper('wikipedia_id'), name='metab_wikipedia_id_idx'),
        ),
        migrations.AddIndex(
            model_name='hmdbmetabolite',
            index=models.Index(django.db.models.functions.text.Upper('iupac_name'), name='metab_iupac_name_idx'),
        ),
        migrations.AddIndex(
            model_name='hmdbmetabolite',
            index=models.Index(django.db.models.functions.text.Upper('traditional_iupac'), name='metab_traditional_iupac_idx'),
        ),
        migrations.AddIndex(
            model_name='hmdbmetabolite',
            index=models.Index(models.F('bigg_id'), name='metab_bigg_id_idx'),
        ),
        migrations.AddIndex(
            model_name='hmdbmetabolite',
            index=models.Index(models.F('pubchem_compound_id'), name='metab_pubchem_compound_idx'),
        ),
        migrations.AddIndex(
            model_name='hmdbmetabolite',
            index=models.Index(models.F('chemspider_id'), name='metab_chemspider_id_idx'),
        ),
        migrations.AddIndex(
            model_name='hmdbmetabolite',
            index=models.Index(models.F('chebi_id'), name='metab_chebi_id_idx'),
        ),
        migrations.AddIndex(
            model_name='metabolitesynonym',
            index=models.Index(django.db.models.functions.text.Upper('value'), name='metab_synonym_idx'),
        ),
        migrations.AddIndex(
            model_name='omimid',
            index=models.Index(models.F('value'), name='omimid_value_idx'),
        ),
        migrations.AddIndex(
            model_name='secondaryaccession',
            index=models.Index(django.db.models.functions.text.Upper('value'), name='metab_second_acc_idx'),
        ),
    ]
