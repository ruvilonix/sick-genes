from django.db import models
from django.db.models import Lookup
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.contrib.postgres.fields import ArrayField

@ArrayField.register_lookup
class ArrayIContains(Lookup):
    lookup_name = "icontains"

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = rhs_params + lhs_params
        return "%s ILIKE ANY(%s)" % (rhs, lhs), params

class Study(models.Model):
    title = models.CharField(max_length=300, verbose_name="Title")
    doi = models.CharField(max_length=100, verbose_name="DOI URL", unique=True)
    publisher_url = models.CharField(max_length=300, verbose_name="Publisher's URL", null=True, blank=True)
    s4me_url = models.CharField(max_length=300, verbose_name="S4ME URL", null=True, blank=True)
    preprint = models.BooleanField(default=False, verbose_name="Preprint")

    date_added = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'studies'

    def get_absolute_url(self):
        return reverse('sickgenes:study', kwargs={'pk': self.pk})
    
    def __str__(self):
        return self.title
    
class Disease(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
    
class StudyCohort(models.Model):
    study = models.ForeignKey(Study, on_delete=models.CASCADE)
    disease = models.ManyToManyField(Disease, related_name="disease_study_cohorts")
    control = models.ManyToManyField(Disease, related_name="control_study_cohorts")

    def __str__(self):
        disease_names = ", ".join([d.name for d in self.disease.all()])
        control_names = ", ".join([c.name for c in self.control.all()])
        return f"[{self.study.title[:20]}]... - [{disease_names}]/[{control_names}]"
    
class Finding(models.Model):
    class FindingType(models.TextChoices):
        VARIATION = "V", _("Genetic variation")
        ABUNDANCE = "A", _("Molecular abundance")

    study_cohort = models.ForeignKey(StudyCohort, on_delete=models.CASCADE)
    hgnc_gene = models.ForeignKey('HgncGene', on_delete=models.PROTECT, null=True, default=None)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['study_cohort', 'hgnc_gene'], name='unique_study_gene'),
        ]

    def __str__(self):
        return f"[{self.study_cohort.study.title[:20]}]... - {self.hgnc_gene}"