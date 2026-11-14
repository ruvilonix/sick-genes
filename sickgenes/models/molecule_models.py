from django.db import models
from .managers import HgncGeneManager
from django.db.models.functions import Upper
from django.urls import reverse


class HgncGene(models.Model):
    hgnc_id = models.IntegerField(unique=True)
    symbol = models.CharField(max_length=30)
    name = models.CharField(max_length=255, default=None, null=True)
    entrez_id = models.BigIntegerField(null=True)
    ensembl_gene_id = models.CharField(max_length=20, null=True)
    vega_id = models.CharField(max_length=25, null=True)
    ucsc_id = models.CharField(max_length=15, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    objects = HgncGeneManager()

    class Meta:
        ordering = ['symbol']

        indexes = [
            models.Index(Upper('symbol'), name='hgncgene_symbol_iexact_idx'),
            models.Index(Upper('name'), name='hgncgene_name_iexact_idx'),
            models.Index('entrez_id', name='hgncgene_entrez_id_idx'),
            models.Index(Upper('ensembl_gene_id'), name='hgncgene_ensembl_iexact_idx'),
            models.Index(Upper('vega_id'), name='hgncgene_vega_id_iexact_idx'),
            models.Index(Upper('ucsc_id'), name='hgncgene_ucsc_id_iexact_idx'),
        ]
    
    def __str__(self):
        return self.symbol
    
    def get_absolute_url(self):
        return reverse('sickgenes:gene_detail', kwargs={'hgnc_symbol': self.symbol})

class BaseGeneAssociation(models.Model):
    gene = models.ForeignKey(HgncGene, on_delete=models.CASCADE)

    class Meta:
        abstract = True
        unique_together = ('gene', 'value')
        
        indexes = [
            models.Index(Upper('value'), name='%(class)s_value_idx')
        ]

    def __str__(self):
        return str(self.value)

class Ena(BaseGeneAssociation):
    value = models.CharField(max_length=15)
class UniprotId(BaseGeneAssociation):
    value = models.CharField(max_length=15)
class OmimId(BaseGeneAssociation):
    value = models.IntegerField()

    class Meta:
        unique_together = ('gene', 'value')
        indexes = [
            models.Index('value', name='omimid_value_idx')
        ]

class AliasSymbol(BaseGeneAssociation):
    value = models.CharField(max_length=40)
class AliasName(BaseGeneAssociation):
    value = models.CharField(max_length=255)
class PrevSymbol(BaseGeneAssociation):
    value = models.CharField(max_length=40)
class PrevName(BaseGeneAssociation):
    value = models.CharField(max_length=255)
