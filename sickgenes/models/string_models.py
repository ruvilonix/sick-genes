from django.db import models
from sickgenes.models import HgncGene

class StringProtein(models.Model):
    protein_id = models.CharField(max_length=16, unique=True)
    hgnc_id = models.CharField(max_length=11)
    hgnc_gene = models.ForeignKey(HgncGene, on_delete=models.CASCADE)

    def __str__(self):
        return self.protein_id
    
class StringInteraction(models.Model):
    protein1 = models.ForeignKey(StringProtein, on_delete=models.CASCADE, related_name='protein1_interactions')
    protein2 = models.ForeignKey(StringProtein, on_delete=models.CASCADE, related_name='protein2_interactions')
    combined_score = models.SmallIntegerField()

    def __str__(self):
        return f'{str(self.protein1)} - {str(self.protein2)}: {self.combined_score}'
    
    class Meta:
        indexes = [
            models.Index(fields=['protein1'], name='stringinteraction_protein1_idx'),
            models.Index(fields=['protein2'], name='stringinteraction_protein2_idx'),
        ]