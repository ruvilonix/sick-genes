from django.db import models
from django.db.models import Lookup
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
import re

@ArrayField.register_lookup
class ArrayIContains(Lookup):
    lookup_name = "icontains"

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = rhs_params + lhs_params
        return "%s ILIKE ANY(%s)" % (rhs, lhs), params

class Study(models.Model):
    title = models.CharField(max_length=500, verbose_name="Title")
    doi = models.CharField(max_length=255, verbose_name="DOI URL", unique=True)
    publisher_url = models.CharField(max_length=300, verbose_name="Publisher's URL", null=True, blank=True)
    authors = models.TextField(blank=True, null=True)
    
    publication_year = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Publication Year")
    publication_month = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Publication Month")
    publication_day = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Publication Day")

    s4me_url = models.CharField(max_length=300, verbose_name="S4ME URL", null=True, blank=True)
    preprint = models.BooleanField(default=False, verbose_name="Preprint")

    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def clean(self):
        super().clean()
        if self.doi:
            normalized_doi = self.normalize_doi(self.doi) 
            if not normalized_doi:
                raise ValidationError({'doi': 'Invalid DOI format.'})
            self.doi = normalized_doi

    @staticmethod
    def normalize_doi(doi_string):
        """
        Cleans a DOI string
        """
        if not doi_string:
            return None
        normalized_doi = re.sub(r'^(https?:\/\/)?(dx\.)?doi\.org\/', '', doi_string.strip(), flags=re.IGNORECASE)
        
        if not normalized_doi.startswith('10.'):
            return None
            
        return normalized_doi

    class Meta:
        verbose_name_plural = 'studies'

    def get_absolute_url(self):
        return reverse('sickgenes:study', kwargs={'study_id': self.pk})
    
    def __str__(self):
        return self.title if self.title else self.doi
    
class Disease(models.Model):
    name = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return self.name
    
class StudyCohort(models.Model):
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name='study_cohorts')
    disease_tags = models.ManyToManyField(Disease, related_name="disease_study_cohorts")
    control_tags = models.ManyToManyField(Disease, related_name="control_study_cohorts")
    note = models.TextField(default=None, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        disease_names = ", ".join([d.name for d in self.disease_tags.all()])
        control_names = ", ".join([c.name for c in self.control_tags.all()])
        return f"[{self.study.title[:20]}]... - [{disease_names}]/[{control_names}]"
    
class GeneFindingType(models.TextChoices):
    VARIATION = "V", "Genetic variation"
    ABUNDANCE = "A", "Molecular abundance"
    
class GeneFinding(models.Model):
    study_cohort = models.ForeignKey(StudyCohort, on_delete=models.CASCADE, related_name="gene_findings")
    hgnc_gene = models.ForeignKey('HgncGene', on_delete=models.PROTECT, null=True, default=None)
    type = models.CharField(max_length=1, choices=GeneFindingType.choices, default=None, null=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['study_cohort', 'hgnc_gene', 'type'], name='unique_study_gene_type'),

            models.CheckConstraint(
                name="%(app_label)s_%(class)s_type_valid",
                check=models.Q(type__in=GeneFindingType.values),
            )
        ]

    def __str__(self):
        return f"[{self.study_cohort.study.title[:20]}]... - {self.hgnc_gene}"
    
class MetaboliteFinding(models.Model):
    study_cohort = models.ForeignKey(StudyCohort, on_delete=models.CASCADE, related_name="metabolite_findings")
    hmdb_metabolite = models.ForeignKey('HmdbMetabolite', on_delete=models.PROTECT, null=True, default=None)

    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['study_cohort', 'hmdb_metabolite'], name='unique_study_cohort_metabolite_'),
        ]

    def __str__(self):
        return f"[{self.study_cohort.study.title[:20]}]... - {self.hmdb_metabolite}"