from django.db import models
from django.contrib.postgres.fields import ArrayField

class HgncGene(models.Model):
    hgnc_id = models.CharField(max_length=15, default=None, unique=True)
    symbol = models.CharField(max_length=30, default=None, null=True)
    name = models.CharField(max_length=200, default=None, null=True)

    entrez_id = models.CharField(max_length=15, default=None, null=True)
    ensembl_gene_id = models.CharField(max_length=20, default=None, null=True)
    vega_id = models.CharField(max_length=25, default=None, null=True)
    ucsc_id = models.CharField(max_length=15, default=None, null=True)

    ena = ArrayField(models.CharField(max_length=15, default=None, null=True), default=list)
    uniprot_ids = ArrayField(models.CharField(max_length=15, default=None, null=True), default=list)
    pubmed_id = ArrayField(models.BigIntegerField(default=None, null=True), default=list)
    omim_id = ArrayField(models.IntegerField(default=None, null=True), default=list)

    alias_symbol = ArrayField(models.CharField(max_length=40, default=None, null=True), default=list)
    alias_name = ArrayField(models.CharField(max_length=200, default=None, null=True), default=list)
    prev_symbol = ArrayField(models.CharField(max_length=25, default=None, null=True), default=list)
    prev_name = ArrayField(models.CharField(max_length=200, default=None, null=True), default=list)

    datetime_updated = models.DateTimeField(null=True)

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
    accession = models.CharField(max_length=20)
    name = models.CharField(max_length=500)