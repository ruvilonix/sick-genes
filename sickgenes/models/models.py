from django.db import models
from django.db.models import Lookup
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from datetime import date
from solo.models import SingletonModel
from django.utils.text import slugify
import re

class SiteConfiguration(SingletonModel):
    site_name = models.CharField(max_length=255, default='Site Name')
    home_page_description = models.TextField(blank=True, null=True, default='')
    about = models.TextField(blank=True, null=True, default='')

    def __str__(self):
        return "Site Configuration"

    class Meta:
        verbose_name = "Site Configuration"

class Study(models.Model):
    title = models.CharField(max_length=500, verbose_name="Title")
    doi = models.CharField(max_length=255, verbose_name="DOI URL", unique=True, null=True, blank=True)
    pmid = models.IntegerField(null=True, blank=True, default=None, verbose_name="PubMed ID")
    publisher_url = models.CharField(max_length=300, verbose_name="Publisher's URL", null=True, blank=True)
    authors = models.TextField(blank=True, null=True)
    journal_titles = models.TextField(null=True, blank=True)
    
    publication_year = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Publication Year")
    publication_month = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Publication Month")
    publication_day = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Publication Day")

    s4me_url = models.CharField(max_length=300, verbose_name="S4ME URL", null=True, blank=True)
    preprint = models.BooleanField(default=False, verbose_name="Preprint")

    not_finished = models.BooleanField(default=False)

    note = models.TextField(null=True, blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    slug = models.SlugField(
        max_length=250,
        null=True,
        blank=True,
    )

    def save(self, *args, **kwargs):
        self.slug = slugify(f'{self.title[:80]}-{self.publication_year}')
        super(Study, self).save(*args, **kwargs)

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
    
    @property
    def publication_date(self):
        """
        Returns a formatted publication date string, e.g., "15 Jul 2024".
        Handles missing day or month.
        """
        if not self.publication_year:
            return "N/A"
        
        parts = []
        if self.publication_day:
            parts.append(str(self.publication_day))
        
        if self.publication_month:
            month_abbr = date(1900, self.publication_month, 1).strftime('%b')
            parts.append(month_abbr)
            
        parts.append(str(self.publication_year))
        
        return " ".join(parts)
    
    @property
    def short_authors(self):
        if not self.authors:
            return ''
        authors = self.authors.split(';')
        first_author_last_name = authors[0].split(',')[0].strip()
        if len(authors) > 1:
            return first_author_last_name + ' et al.'
        else:
            return first_author_last_name
    
    @property
    def first_journal_title(self):
        """Returns the first journal title from the semi-colon separated list."""
        if not self.journal_titles:
            return None
        return self.journal_titles.split(';')[0].strip()

    class Meta:
        verbose_name_plural = 'studies'

    def get_absolute_url(self):
        return reverse('sickgenes:study', kwargs={'study_id': self.pk, 'slug': self.slug})
    
    def __str__(self):
        return self.title if self.title else self.doi
    
class Disease(models.Model):
    name = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']
    
class StudyCohort(models.Model):
    study = models.ForeignKey(Study, on_delete=models.CASCADE, related_name='study_cohorts')
    disease_tags = models.ManyToManyField(Disease, related_name="study_cohorts")
    note = models.TextField(default=None, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        disease_names = ", ".join([d.name for d in self.disease_tags.all()])
        return f"[{self.study.title[:20]}]... - [{disease_names}]"
    
class GeneFinding(models.Model):
    study_cohort = models.ForeignKey(StudyCohort, on_delete=models.CASCADE, related_name="gene_findings")
    hgnc_gene = models.ForeignKey('HgncGene', on_delete=models.PROTECT, null=True, default=None)

    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['study_cohort', 'hgnc_gene'], name='unique_study_gene'),
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