from django.db import models
from sickgenes.models import HgncGene

class StringProtein(models.Model):
    protein_id = models.CharField(max_length=16, unique=True)
    hgnc_id = models.CharField(max_length=11)
    hgnc_gene = models.ForeignKey(HgncGene, on_delete=models.CASCADE)

    def __str__(self):
        return self.protein_id