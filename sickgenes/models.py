from django.db import models
from sickgenes.managers import MoleculeManager
from django.utils.translation import gettext_lazy as _
from django.urls import reverse

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
    molecule = models.ForeignKey('Molecule', on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['study_cohort', 'molecule'], name='unique_study_gene'),
        ]

    def __str__(self):
        return f"[{self.study_cohort.study.title[:20]}]... - {self.molecule}"

class Molecule(models.Model):
    class MoleculeType(models.TextChoices):
        GENE = "G", _("Gene")
        METABOLITE = "M", _("Metabolite")

    hgnc_id = models.CharField(max_length=40, default=None, unique=True, null=True)
    hgnc_symbol = models.CharField(max_length=50, default=None, unique=True, null=True)
    hgnc_name = models.CharField(max_length=250, default=None, null=True)

    hmdb_accession = models.CharField(max_length=100, default=None, unique=True, null=True)
    hmdb_name = models.CharField(max_length=400, default=None, unique=True, null=True)

    type = models.CharField(max_length=1, choices=MoleculeType)

    datetime_updated = models.DateTimeField(null=True)

    objects = MoleculeManager()

    class Meta:
        verbose_name = 'molecule'
        verbose_name_plural = 'molecules'

        ordering = ['hgnc_symbol', 'hmdb_name']

        indexes = [
            models.Index(fields=['type'], name='molecule_type'),
        ]


    def __str__(self):
        if self.type == self.MoleculeType.GENE:
            return self.hgnc_symbol
        elif self.type == self.MoleculeType.METABOLITE:
            return self.hmdb_name
        else:
            return '<NO NAME>'
        
    # TODO add check constraint where if type is GENE, hgnc_id must be set, and similar for METABOLITE and hmdb_accession

class MoleculeAlias(models.Model):
    molecule = models.ForeignKey(Molecule, on_delete=models.CASCADE)
    alias = models.CharField(max_length=50)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['molecule', 'alias'],
                name='unique_molecule_alias',
            )
        ]

        ordering = ['alias']

        verbose_name = 'molecule alias'
        verbose_name_plural = 'molecule aliases'

    def __str__(self):
        return self.alias