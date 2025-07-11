from django.db import models
from .managers import HgncGeneManager, HmdbMetaboliteManager
from django.db.models.functions import Upper


class HgncGene(models.Model):
    hgnc_id = models.CharField(max_length=15, unique=True, null=True, default=None)
    symbol = models.CharField(max_length=30, null=True)
    name = models.CharField(max_length=255, default=None, null=True)
    entrez_id = models.CharField(max_length=15, null=True)
    ensembl_gene_id = models.CharField(max_length=20, null=True)
    vega_id = models.CharField(max_length=25, null=True)
    ucsc_id = models.CharField(max_length=15, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    objects = HgncGeneManager()

    class Meta:
        ordering = ['symbol']

        indexes = [
            models.Index(Upper('hgnc_id'), name='hgncgene_hgncid_iexact_idx'),
            models.Index(Upper('symbol'), name='hgncgene_symbol_iexact_idx'),
            models.Index(Upper('name'), name='hgncgene_name_iexact_idx'),
            models.Index(Upper('entrez_id'), name='hgncgene_entrez_id_iexact_idx'),
            models.Index(Upper('ensembl_gene_id'), name='hgncgene_ensembl_iexact_idx'),
            models.Index(Upper('vega_id'), name='hgncgene_vega_id_iexact_idx'),
            models.Index(Upper('ucsc_id'), name='hgncgene_ucsc_id_iexact_idx'),
        ]
    
    def __str__(self):
        return self.symbol or self.hgnc_id

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
        indexes = []

class AliasSymbol(BaseGeneAssociation):
    value = models.CharField(max_length=40)
class AliasName(BaseGeneAssociation):
    value = models.CharField(max_length=255)
class PrevSymbol(BaseGeneAssociation):
    value = models.CharField(max_length=40)
class PrevName(BaseGeneAssociation):
    value = models.CharField(max_length=255)
    

class HmdbMetabolite(models.Model):
    accession = models.CharField(max_length=15, unique=True)
    name = models.CharField(max_length=255)
    cas_registry_number = models.CharField(max_length=15, default=None, null=True)
    drugbank_id = models.CharField(max_length=15, default=None, null=True)
    foodb_id = models.CharField(max_length=15, default=None, null=True)
    knapsack_id = models.CharField(max_length=25, default=None, null=True)
    biocyc_id = models.CharField(max_length=55, default=None, null=True)
    wikipedia_id = models.CharField(max_length=100, default=None, null=True)
    iupac_name = models.CharField(max_length=255, default=None, null=True)
    traditional_iupac = models.CharField(max_length=255, default=None, null=True)
    bigg_id = models.IntegerField(default=None, null=True)
    pubchem_compound_id = models.IntegerField(default=None, null=True)
    chemspider_id = models.IntegerField(default=None, null=True)
    chebi_id = models.IntegerField(default=None, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    objects = HmdbMetaboliteManager()

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class MetaboliteSynonym(models.Model):
    metabolite = models.ForeignKey(HmdbMetabolite, on_delete=models.CASCADE, related_name="synonyms")
    value = models.CharField(max_length=255)

    class Meta:
        unique_together = ('metabolite', 'value')

    def __str__(self):
        return self.value

class SecondaryAccession(models.Model):
    metabolite = models.ForeignKey(HmdbMetabolite, on_delete=models.CASCADE, related_name="secondary_accessions")
    value = models.CharField(max_length=15)

    class Meta:
        unique_together = ('metabolite', 'value')

    def __str__(self):
        return self.value