from django.db import models
from sickgenes.choices import HgncGeneExtraFieldType

class HgncGene(models.Model):
    hgnc_id = models.CharField(max_length=40, default=None, unique=True, null=True)
    symbol = models.CharField(max_length=50, default=None, null=True)
    name = models.CharField(max_length=250, default=None, null=True)

    datetime_updated = models.DateTimeField(null=True)

    class Meta:
        ordering = ['symbol']

        indexes = [
            models.Index(fields=['symbol'], name='hgncgene_symbol_idx'),
            models.Index(fields=['name'], name='hgncgene_name_idx'),
        ]


    def __str__(self):
        return self.symbol
    
class HgncGeneExtra(models.Model):
    hgnc_gene = models.ForeignKey(HgncGene, on_delete=models.CASCADE)
    value = models.CharField(max_length=300)
    field_name = models.CharField(max_length=3, choices=HgncGeneExtraFieldType, default=None, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['value'], name='hgncgeneextra_value_idx'),
            models.Index(fields=['field_name'], name='hgncgeneextra_fieldname_idx'),
        ]

        ordering = ['field_name', 'value']

    def __str__(self):
        return self.value