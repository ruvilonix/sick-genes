from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from sickgenes.managers import HgncGeneManager, HmdbMetaboliteManager

class HgncGene(models.Model):
    hgnc_id = models.CharField(max_length=15, default=None, unique=True)
    symbol = models.CharField(max_length=30, default=None, null=True)
    name = models.CharField(max_length=200, default=None, null=True)

    entrez_id = models.CharField(max_length=15, default=None, null=True)
    ensembl_gene_id = models.CharField(max_length=20, default=None, null=True)
    vega_id = models.CharField(max_length=25, default=None, null=True)
    ucsc_id = models.CharField(max_length=15, default=None, null=True)

    ena = ArrayField(models.CharField(max_length=15), default=list)
    uniprot_ids = ArrayField(models.CharField(max_length=15), default=list)
    omim_id = ArrayField(models.IntegerField(), default=list)

    alias_symbol = ArrayField(models.CharField(max_length=40), default=list)
    alias_name = ArrayField(models.CharField(max_length=200), default=list)
    prev_symbol = ArrayField(models.CharField(max_length=25), default=list)
    prev_name = ArrayField(models.CharField(max_length=200), default=list)

    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    objects = HgncGeneManager()

    class Meta:
        ordering = ['symbol']

        indexes = [
            models.Index(fields=['symbol'], name='hgncgene_symbol_idx'),
            models.Index(fields=['name'], name='hgncgene_name_idx'),

            models.Index(fields=['entrez_id'], name='hgncgene_entrez_id_idx'),
            models.Index(fields=['ensembl_gene_id'], name='hgncgene_ensembl_gene_id_idx'),
            models.Index(fields=['vega_id'], name='hgncgene_vega_id_idx'),
            models.Index(fields=['ucsc_id'], name='hgncgene_ucsc_id_idx'),
        ]


    def __str__(self):
        return self.symbol
    
class HmdbMetabolite(models.Model):
    accession = models.CharField(max_length=15, unique=True)
    name = models.CharField(max_length=255)

    cas_registry_number = models.CharField(max_length=15, default=None, null=True)
    drugbank_id = models.CharField(max_length=15, default=None, null=True)
    foodb_id = models.CharField(max_length=15, default=None, null=True)
    knapsack_id = models.CharField(max_length=25, default=None, null=True)
    biocyc_id = models.CharField(max_length=55, default=None, null=True)
    wikipedia_id = models.CharField(max_length=100, default=None, null=True)

    iupac_name = models.CharField(default=None, null=True)
    traditional_iupac = models.CharField(default=None, null=True)

    bigg_id = models.IntegerField(default=None, null=True)
    pubchem_compound_id = models.IntegerField(default=None, null=True)
    chemspider_id = models.IntegerField(default=None, null=True)
    chebi_id = models.IntegerField(default=None, null=True)

    secondary_accessions = ArrayField(models.CharField(max_length=15), default=list)
    synonyms = ArrayField(models.CharField(), default=list)

    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    objects = HmdbMetaboliteManager()

    class Meta:
        ordering = ['name']

        indexes = [
            models.Index(fields=['accession'], name='hmdbmetabolite_accession_idx'),
            models.Index(fields=['name'], name='hmdbmetabolite_name_idx'),
            models.Index(fields=['cas_registry_number'], name='hmdbmetabolite_cas_num_idx'),
            models.Index(fields=['drugbank_id'], name='hmdbmetabolite_drugbank_id_idx'),
            models.Index(fields=['foodb_id'], name='hmdbmetabolite_foodb_id_idx'),
            models.Index(fields=['knapsack_id'], name='hmdbmetabolite_knapsack_id_idx'),
            models.Index(fields=['biocyc_id'], name='hmdbmetabolite_biocyc_id_idx'),
            models.Index(fields=['wikipedia_id'], name='hmdbmetabolite_wiki_id_idx'),

            models.Index(fields=['iupac_name'], name='hmdbmetabolite_iupac_name_idx'),
            models.Index(fields=['traditional_iupac'], name='hmdbmetabolite_tradiupac_idx'),

            models.Index(fields=['bigg_id'], name='hmdbmetabolite_bigg_id_idx'),
            models.Index(fields=['pubchem_compound_id'], name='hmdbmetabolite_pubchem_idx'),
            models.Index(fields=['chemspider_id'], name='hmdbmetabolite_chemspider_idx'),
            models.Index(fields=['chebi_id'], name='hmdbmetabolite_chebi_id_idx'),

            GinIndex(fields=['secondary_accessions'], name='hmdbmetabolite_secondary_idx'),
            GinIndex(fields=['synonyms'], name='hmdbmetabolite_synonyms_idx'),

        ]

    def __str__(self):
        return self.name