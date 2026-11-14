import time
from django.test.utils import CaptureQueriesContext
from django.db import IntegrityError, connection
from django.test import SimpleTestCase, TestCase
from django.core.management import call_command
from sickgenes.models import Study, Disease, StudyCohort
from io import StringIO
from django.utils import timezone
from django.urls import reverse
from sickgenes.forms import StudyForm, SetNewestStudyVersionForm
from sickgenes.models import (
    HgncGene, Ena, UniprotId, OmimId, AliasSymbol, AliasName, PrevSymbol, PrevName,
    HmdbMetabolite, MetaboliteSynonym, SecondaryAccession, GeneFinding, SiteConfiguration
)
from unittest.mock import patch, Mock
import requests
from django.contrib.messages import get_messages
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.auth import get_user_model
from sickgenes.views.doi_lookup import parse_crossref_work

class GeneListTests(TestCase):
    """
    Tests for the gene_list view.
    """
    @classmethod
    def setUpTestData(cls):
        """Set up non-modified objects used by all test methods."""
        # Create Diseases
        cls.disease1 = Disease.objects.create(name='Cardiomyopathy')
        cls.disease2 = Disease.objects.create(name='Epilepsy')

        # Create Genes
        cls.gene_brca1 = HgncGene.objects.create(hgnc_id=1100, symbol='BRCA1')
        cls.gene_scn1a = HgncGene.objects.create(hgnc_id=10585, symbol='SCN1A')
        cls.gene_ttn = HgncGene.objects.create(hgnc_id=12403, symbol='TTN')
        cls.gene_abc = HgncGene.objects.create(hgnc_id=1, symbol="ABC")
        cls.gene_def = HgncGene.objects.create(hgnc_id=2, symbol="DEF")

        # Create Studies
        cls.study1 = Study.objects.create(title='Cardio Study A', publication_year=2020)
        cls.study2 = Study.objects.create(title='Neuro Study B', publication_year=2021)
        cls.study3 = Study.objects.create(title='Multi-gene Study C', publication_year=2022)
        cls.study4 = Study.objects.create(title="Not finished study", not_finished=True)

        # Create Study Cohorts and link diseases
        cls.cohort1 = StudyCohort.objects.create(study=cls.study1)
        cls.cohort1.disease_tags.add(cls.disease1)

        cls.cohort2 = StudyCohort.objects.create(study=cls.study2)
        cls.cohort2.disease_tags.add(cls.disease2)
        
        cls.cohort3 = StudyCohort.objects.create(study=cls.study3)
        cls.cohort3.disease_tags.add(cls.disease1, cls.disease2)

        cls.cohort4 = StudyCohort.objects.create(study=cls.study4)
        cls.cohort4.disease_tags.add(cls.disease1)

        # Create GeneFindings to link genes to cohorts
        # Gene TTN is in two studies (Study1, Study3)
        GeneFinding.objects.create(hgnc_gene=cls.gene_ttn, study_cohort=cls.cohort1)
        GeneFinding.objects.create(hgnc_gene=cls.gene_ttn, study_cohort=cls.cohort3)
        
        # Gene SCN1A is in two studies (Study2, Study3)
        GeneFinding.objects.create(hgnc_gene=cls.gene_scn1a, study_cohort=cls.cohort2)
        GeneFinding.objects.create(hgnc_gene=cls.gene_scn1a, study_cohort=cls.cohort3)

        # Gene DEF only in Epilepsy study
        GeneFinding.objects.create(hgnc_gene=cls.gene_def, study_cohort=cls.cohort2)

        # Gene BRCA1 is only in one study (Study3)
        GeneFinding.objects.create(hgnc_gene=cls.gene_brca1, study_cohort=cls.cohort3)

        GeneFinding.objects.create(hgnc_gene=cls.gene_abc, study_cohort=cls.cohort4)
        
    def test_gene_list_view_loads_successfully(self):
        """
        Tests that the gene list page returns a 200 OK response.
        """
        response = self.client.get(reverse('sickgenes:gene_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sickgenes/gene_list.html')
        self.assertIn('form', response.context)
        self.assertIn('genes_table', response.context)

    def _symbols_in_table(self, response):
        return {gene.symbol for gene in response.context['genes_table'].data}

    def test_gene_list_filters_by_comma_separated_symbols(self):
        response = self.client.get(reverse('sickgenes:gene_list') + '?symbol=TTN,BRCA1')
        self.assertEqual(self._symbols_in_table(response), {'TTN', 'BRCA1'})
        self.assertContains(response, 'name="symbol" value="TTN,BRCA1"')

    def test_gene_list_filters_by_repeated_symbol_params(self):
        # Old style links should keep working
        response = self.client.get(reverse('sickgenes:gene_list') + '?symbol=TTN&symbol=BRCA1')
        self.assertEqual(self._symbols_in_table(response), {'TTN', 'BRCA1'})

    def test_gene_list_accepts_many_comma_separated_symbols(self):
        symbols = ['TTN'] + [f'FAKE{i}' for i in range(2000)]
        response = self.client.get(reverse('sickgenes:gene_list') + '?symbol=' + ','.join(symbols))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._symbols_in_table(response), {'TTN'})

    def test_gene_list_filters_by_cohort(self):
        response = self.client.get(reverse('sickgenes:gene_list') + f'?cohort={self.cohort3.id}')
        genes = {gene.symbol: gene for gene in response.context['genes_table'].data}
        self.assertEqual(set(genes), {'TTN', 'SCN1A', 'BRCA1'})
        # Study counts still cover all studies, not just this cohort
        self.assertEqual(genes['TTN'].study_count, 2)
        self.assertContains(response, f'name="cohort" value="{self.cohort3.id}"')

    def test_gene_list_cohort_of_unfinished_study_hidden_from_public(self):
        response = self.client.get(reverse('sickgenes:gene_list') + f'?cohort={self.cohort4.id}')
        self.assertEqual(self._symbols_in_table(response), set())

    def test_gene_list_cohort_of_unfinished_study_shown_to_staff(self):
        staff = User.objects.create_user('staff', password='pw', is_staff=True)
        self.client.force_login(staff)
        response = self.client.get(reverse('sickgenes:gene_list') + f'?cohort={self.cohort4.id}')
        self.assertEqual(self._symbols_in_table(response), {'ABC'})

    def test_gene_list_invalid_cohort_ignored(self):
        response = self.client.get(reverse('sickgenes:gene_list') + '?cohort=abc')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._symbols_in_table(response), {'TTN', 'SCN1A', 'BRCA1', 'DEF'})

    def test_gene_list_unfiltered_study_counts(self):
        """
        Tests that the annotated study_count is correct without any filters.
        """
        response = self.client.get(reverse('sickgenes:gene_list'))
        genes_in_context = {gene.symbol: gene for gene in response.context['genes_table'].data}

        # Only genes found in published studies are listed by default.
        # ABC is only in an unfinished study.
        self.assertEqual(set(genes_in_context), {'TTN', 'SCN1A', 'BRCA1', 'DEF'})

        # Verify the study count for each gene
        self.assertEqual(genes_in_context['TTN'].study_count, 2)    # Associated with study1 and study3
        self.assertEqual(genes_in_context['SCN1A'].study_count, 2) # Associated with study2 and study3
        self.assertEqual(genes_in_context['BRCA1'].study_count, 1) # Associated with study3 only

    def test_gene_list_leaves_out_genes_only_in_older_study_versions(self):
        old_version = Study.objects.create(title='Old version', newest_version=self.study1)
        old_cohort = StudyCohort.objects.create(study=old_version)
        old_gene = HgncGene.objects.create(hgnc_id=3, symbol='OLDONLY')
        GeneFinding.objects.create(hgnc_gene=old_gene, study_cohort=old_cohort)

        response = self.client.get(reverse('sickgenes:gene_list'))
        self.assertNotIn('OLDONLY', self._symbols_in_table(response))

    def test_gene_list_filters_by_disease(self):
        """
        Tests that the list is correctly filtered when a disease is selected.
        """
        # Cardiomyopathy (disease1): TTN via cohort1, and TTN/SCN1A/BRCA1 via cohort3
        response = self.client.get(reverse('sickgenes:gene_list'), {'phenotype': self.disease1.pk})
        self.assertEqual(self._symbols_in_table(response), {'TTN', 'SCN1A', 'BRCA1'})

        # Epilepsy (disease2): SCN1A/DEF via cohort2, and TTN/SCN1A/BRCA1 via cohort3
        response = self.client.get(reverse('sickgenes:gene_list'), {'phenotype': self.disease2.pk})
        self.assertEqual(self._symbols_in_table(response), {'TTN', 'SCN1A', 'BRCA1', 'DEF'})

    def test_gene_list_can_include_genes_without_studies(self):
        response = self.client.get(reverse('sickgenes:gene_list'), {'include_unstudied': 'on'})
        genes = {gene.symbol: gene for gene in response.context['genes_table'].data}
        self.assertEqual(len(genes), 5)
        self.assertEqual(genes['ABC'].study_count, 0)

    def test_gene_search_results_include_genes_without_studies(self):
        response = self.client.get(reverse('sickgenes:gene_list'), {'symbol': 'ABC,TTN'})
        self.assertEqual(self._symbols_in_table(response), {'ABC', 'TTN'})
        self.assertNotContains(response, 'include_unstudied')

    def test_gene_list_disease_filter_annotated_counts(self):
        """
        Tests that when filtering by disease, the list still includes all genes,
        but the study_count is correctly annotated based on the filter.
        """
        # Filter by Cardiomyopathy (disease1)
        url = f"{reverse('sickgenes:gene_list')}?phenotype={self.disease1.pk}&include_unstudied=on"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Convert the context data to a dictionary for easy lookups
        genes_in_context = {gene.symbol: gene for gene in response.context['genes_table'].data}

        # Including genes without studies lists all 5 (TTN, SCN1A, BRCA1, ABC, DEF)
        self.assertEqual(len(genes_in_context), 5)

        # --- Verify the annotated study_count for each gene ---

        # TTN is in Study1 (Cardio) and Study3 (Cardio), so count = 2
        self.assertEqual(genes_in_context['TTN'].study_count, 2)
        
        # SCN1A is in Study3 (Cardio), so count = 1
        self.assertEqual(genes_in_context['SCN1A'].study_count, 1)

        # BRCA1 is in Study3 (Cardio), so count = 1
        self.assertEqual(genes_in_context['BRCA1'].study_count, 1)

        # DEF is only in an Epilepsy study, so its count for Cardiomyopathy is 0
        self.assertEqual(genes_in_context['DEF'].study_count, 0)

class GeneDetailTests(TestCase):
    """
    Tests for the gene_detail view.
    """
    @classmethod
    def setUpTestData(cls):
        """Set up non-modified objects used by all test methods."""
        # Create SiteConfiguration to prevent it from being created during the test
        SiteConfiguration.objects.create(id=1, site_name='Test Site', about='')

        # Create a single gene to test in detail
        cls.gene = HgncGene.objects.create(pk=1, hgnc_id=12403, symbol='TTN')

        # Create studies with different publication years for sorting test
        cls.study_2022 = Study.objects.create(title='Newer Study', publication_year=2022)
        cls.study_2020 = Study.objects.create(title='Older Study', publication_year=2020)
        cls.study_no_year = Study.objects.create(title='Study with no year', publication_year=None)
        cls.study_not_finished = Study.objects.create(title='Not finished notating study', not_finished=True)

        # Create cohorts belonging to the studies
        # Two cohorts are in the same study to test grouping
        cls.cohort_a_2022 = StudyCohort.objects.create(study=cls.study_2022)
        cls.cohort_b_2022 = StudyCohort.objects.create(study=cls.study_2022)
        cls.cohort_c_2020 = StudyCohort.objects.create(study=cls.study_2020)
        cls.cohort_d_notfinihsed = StudyCohort.objects.create(study=cls.study_not_finished)
        
        # Link the gene to these cohorts
        GeneFinding.objects.create(hgnc_gene=cls.gene, study_cohort=cls.cohort_a_2022)
        GeneFinding.objects.create(hgnc_gene=cls.gene, study_cohort=cls.cohort_b_2022)
        GeneFinding.objects.create(hgnc_gene=cls.gene, study_cohort=cls.cohort_c_2020)
        GeneFinding.objects.create(hgnc_gene=cls.gene, study_cohort=cls.cohort_d_notfinihsed)

        # Create another gene and finding that should NOT appear on the detail page
        other_gene = HgncGene.objects.create(pk=2, hgnc_id=1, symbol='OTHER')
        other_cohort = StudyCohort.objects.create(study=cls.study_2022)
        GeneFinding.objects.create(hgnc_gene=other_gene, study_cohort=other_cohort)

    def test_gene_detail_view_loads_successfully(self):
        """
        Tests that the gene detail page for an existing gene returns a 200 OK response.
        """
        response = self.client.get(reverse('sickgenes:gene_detail', kwargs={'hgnc_symbol': self.gene.symbol}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sickgenes/gene_detail.html')
        self.assertEqual(response.context['gene'], self.gene)

    def test_gene_detail_view_returns_404_for_invalid_pk(self):
        """
        Tests that the view returns a 404 Not Found for a non-existent gene PK.
        """
        response = self.client.get(reverse('sickgenes:gene_detail', kwargs={'hgnc_symbol': 'NOTREAL'}))
        self.assertEqual(response.status_code, 404)

    def gene_url(self, symbol):
        return reverse('sickgenes:gene_detail', kwargs={'hgnc_symbol': symbol})

    def test_lowercase_symbol_redirects_to_current_symbol(self):
        response = self.client.get(self.gene_url('ttn'))
        self.assertRedirects(response, self.gene_url('TTN'), status_code=302)

    def test_previous_symbol_redirects_to_renamed_gene(self):
        PrevSymbol.objects.create(gene=self.gene, value='OLDTTN')
        response = self.client.get(self.gene_url('oldttn'))
        self.assertRedirects(response, self.gene_url('TTN'), status_code=302)

    def test_previous_symbol_of_several_genes_lists_them(self):
        other = HgncGene.objects.get(symbol='OTHER')
        PrevSymbol.objects.create(gene=self.gene, value='SHARED')
        PrevSymbol.objects.create(gene=other, value='SHARED')
        response = self.client.get(self.gene_url('SHARED'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sickgenes/gene_previous_symbol.html')
        self.assertContains(response, self.gene_url('TTN'))
        self.assertContains(response, self.gene_url('OTHER'))

    def test_current_symbol_wins_over_previous_symbol(self):
        # OTHER is also a previous symbol of TTN, but OTHER is a current gene
        PrevSymbol.objects.create(gene=self.gene, value='OTHER')
        response = self.client.get(self.gene_url('OTHER'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['gene'].symbol, 'OTHER')

    def test_studies_data_context_is_correctly_structured_and_sorted(self):
        """
        Tests that 'studies_data' is correctly aggregated, grouped, and sorted.
        """
        response = self.client.get(reverse('sickgenes:gene_detail', kwargs={'hgnc_symbol': self.gene.symbol}))
        self.assertEqual(response.status_code, 200)
        
        studies_data = response.context['studies_data']

        # Should be 2 studies associated with the gene
        self.assertEqual(len(studies_data), 2)
        
        # Check sorting: newest study (2022) should be first
        self.assertEqual(studies_data[0][0], self.study_2022)
        self.assertEqual(studies_data[1][0], self.study_2020)

        # Check study 1 (Newer Study, 2022)
        study1, cohorts1 = studies_data[0]
        self.assertEqual(study1, self.study_2022)
        # Check that both cohorts from this study are present
        self.assertEqual(len(cohorts1), 2)
        self.assertIn(self.cohort_a_2022, cohorts1)
        self.assertIn(self.cohort_b_2022, cohorts1)
        
        # Check study 2 (Older Study, 2020)
        study2, cohorts2 = studies_data[1]
        self.assertEqual(study2, self.study_2020)
        self.assertEqual(len(cohorts2), 1)
        self.assertIn(self.cohort_c_2020, cohorts2)

    def test_study_count_heading(self):
        response = self.client.get(reverse('sickgenes:gene_detail', kwargs={'hgnc_symbol': 'TTN'}))
        self.assertContains(response, 'Found in 2 studies')

    def test_older_study_versions_left_out(self):
        old_version = Study.objects.create(title='Old version', newest_version=self.study_2022)
        GeneFinding.objects.create(
            hgnc_gene=self.gene, study_cohort=StudyCohort.objects.create(study=old_version)
        )
        response = self.client.get(reverse('sickgenes:gene_detail', kwargs={'hgnc_symbol': 'TTN'}))
        studies = [study for study, cohorts in response.context['studies_data']]
        self.assertNotIn(old_version, studies)

    def test_literature_links_search_gene_only_by_default(self):
        response = self.client.get(reverse('sickgenes:gene_detail', kwargs={'hgnc_symbol': 'TTN'}))
        self.assertEqual(response.context['pubmed_url'], 'https://pubmed.ncbi.nlm.nih.gov/?term=%22TTN%22')
        self.assertEqual(response.context['scholar_url'], 'https://scholar.google.com/scholar?q=%22TTN%22')
        self.assertContains(response, '>TTN</a>')

    def test_literature_links_add_disease_from_site_configuration(self):
        config = SiteConfiguration.get_solo()
        config.literature_search_label = 'ME/CFS'
        config.literature_search_terms = 'ME/CFS, myalgic encephalomyelitis , '
        config.save()
        response = self.client.get(reverse('sickgenes:gene_detail', kwargs={'hgnc_symbol': 'TTN'}))
        self.assertEqual(response.context['literature_query'], '"TTN" AND ("ME/CFS" OR "myalgic encephalomyelitis")')
        self.assertContains(response, '>TTN and ME/CFS</a>')

    def test_literature_label_ignored_without_terms(self):
        config = SiteConfiguration.get_solo()
        config.literature_search_label = 'ME/CFS'
        config.save()
        response = self.client.get(reverse('sickgenes:gene_detail', kwargs={'hgnc_symbol': 'TTN'}))
        self.assertEqual(response.context['literature_query'], '"TTN"')
        self.assertNotContains(response, 'and ME/CFS')

    def test_literature_search_uses_name_and_previous_symbols(self):
        from sickgenes.views.views import literature_search_terms
        gene = HgncGene.objects.create(hgnc_id=6018, symbol='IL6', name='interleukin 6')
        PrevSymbol.objects.create(gene=gene, value='IFNB2')
        # A previous symbol that is now another gene's symbol is left out
        PrevSymbol.objects.create(gene=gene, value='OTHER')
        AliasSymbol.objects.create(gene=gene, value='HGF')
        # A previous symbol shared with another gene is left out too
        PrevSymbol.objects.create(gene=gene, value='SHARED')
        PrevSymbol.objects.create(gene=HgncGene.objects.get(symbol='OTHER'), value='SHARED')
        self.assertEqual(literature_search_terms(gene), '("IL6" OR "interleukin 6" OR "IFNB2")')

    def test_literature_search_skips_names_with_comma_separated_parts(self):
        from sickgenes.views.views import literature_search_terms
        gene = HgncGene.objects.create(hgnc_id=4948, symbol='HLA-DRB1', name='major histocompatibility complex, class II, DR beta 1')
        self.assertEqual(literature_search_terms(gene), '"HLA-DRB1"')
        # Commas inside chemical names are fine
        # ...and a trailing note in brackets is dropped, as are very short previous symbols
        gene = HgncGene.objects.create(hgnc_id=30, symbol='A4GALT', name='alpha 1,4-galactosyltransferase (P1PK blood group)')
        PrevSymbol.objects.create(gene=gene, value='P1')
        self.assertEqual(literature_search_terms(gene), '("A4GALT" OR "alpha 1,4-galactosyltransferase")')

    def test_database_query_efficiency(self):
        """
        Verifies that prefetching prevents N+1 query problems.
        The number of queries should be small and constant, regardless of the
        number of related findings, cohorts, etc.
        """
        # We expect 12 queries:
        # - 2 queries for SiteConfiguration (literature search terms, and the context processor)
        # - 1 query for the main HgncGene object
        # - 7 queries for each of the prefetched related sets on HgncGene
        # - 1 query for GeneFinding (with StudyCohort and Study joined)
        # - 1 query for the prefetched study_cohort__disease_tags
        # Total = 2 + 1 + 7 + 1 + 1 = 12 queries
        with self.assertNumQueries(12):
            response = self.client.get(reverse('sickgenes:gene_detail', kwargs={'hgnc_symbol': self.gene.symbol}))
            # Accessing the context data forces the querysets to be evaluated
            self.assertIsNotNone(response.context['gene'])
            self.assertGreater(len(response.context['studies_data']), 0)

class StudyListViewTest(TestCase):
    """
    Test suite for the study_list view.
    """
    @classmethod
    def setUpTestData(cls):
        """
        Set up non-modified objects used by all test methods once for the whole class.
        This is more efficient than setUp() for data that doesn't change.
        """
        # Create Genes
        cls.gene_a = HgncGene.objects.create(hgnc_id=1, symbol="GENA")
        cls.gene_b = HgncGene.objects.create(hgnc_id=2, symbol="GENB")

        # Create Diseases
        cls.disease_x = Disease.objects.create(name="Disease X", code="X")
        cls.disease_y = Disease.objects.create(name="Disease Y", code="Y")

        # Study 1: Linked to Disease X with Gene A
        cls.study1 = Study.objects.create(title="Study 1 About Disease X", not_finished=False, authors='Smith, Bridget; Jones, Tony')
        cohort1 = StudyCohort.objects.create(study=cls.study1)
        cohort1.disease_tags.add(cls.disease_x)
        GeneFinding.objects.create(study_cohort=cohort1, hgnc_gene=cls.gene_a)

        # Study 2: Linked to Disease Y with Gene B
        cls.study2 = Study.objects.create(title="Study 2 About Disease Y", not_finished=False, authors='Lewis, John')
        cohort2 = StudyCohort.objects.create(study=cls.study2)
        cohort2.disease_tags.add(cls.disease_y)
        GeneFinding.objects.create(study_cohort=cohort2, hgnc_gene=cls.gene_b)

        # Study 3: Linked to both diseases
        cls.study3 = Study.objects.create(title="Study 3 About Both Diseases", not_finished=False)
        cohort3x = StudyCohort.objects.create(study=cls.study3)
        cohort3x.disease_tags.add(cls.disease_x)
        GeneFinding.objects.create(study_cohort=cohort3x, hgnc_gene=cls.gene_a)
        cohort3y = StudyCohort.objects.create(study=cls.study3)
        cohort3y.disease_tags.add(cls.disease_y)
        GeneFinding.objects.create(study_cohort=cohort3y, hgnc_gene=cls.gene_b)

        # Study 4: Linked to Disease X, but not_finished=True
        cls.study4 = Study.objects.create(title="Study 4 Unfinished", not_finished=True)
        cohort4 = StudyCohort.objects.create(study=cls.study4)
        cohort4.disease_tags.add(cls.disease_x)
        GeneFinding.objects.create(study_cohort=cohort4, hgnc_gene=cls.gene_a)

        # Study 5: Has a cohort but no genes
        cls.study5 = Study.objects.create(title="Study 5 With No Genes")
        cohort5 = StudyCohort.objects.create(study=cls.study5)
        cohort5.disease_tags.add(cls.disease_x)
        
        cls.url = reverse('sickgenes:study_list')
        cls.table_url = reverse('sickgenes:TableStudy')

    def test_view_url_and_template(self):
        """Tests that the view's URL is accessible and renders the correct template."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sickgenes/study_list.html')

    def test_table_ajax_endpoint_accessible(self):
        """Tests that the AJAX table endpoint is accessible."""
        response = self.client.get(self.table_url)
        self.assertEqual(response.status_code, 200)

    def test_unfiltered_study_list_content(self):
        """Tests the AJAX endpoint without any filters. Should show all studies with gene_count > 0."""
        response = self.client.get(self.table_url)
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')
        
        # Check that studies with genes are present
        self.assertIn('Study 1 About Disease X', content)
        self.assertIn('Study 2 About Disease Y', content)
        self.assertIn('Study 3 About Both Diseases', content)

        # Check that study with no genes is absent
        self.assertNotIn('Study 5 With No Genes', content)

    def test_filtered_study_list_by_disease(self):
        """Tests filtering by a disease given in the table URL."""
        response = self.client.get(reverse('sickgenes:TableStudy', args=[self.disease_x.id]))
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')
        
        # Check that only studies related to Disease X are present
        self.assertIn('Study 1 About Disease X', content)
        self.assertIn('Study 3 About Both Diseases', content)
        
        # Check that other studies are correctly excluded
        self.assertNotIn('Study 2 About Disease Y', content)  # Wrong disease
        self.assertNotIn('Study 4 Unfinished', content)  # Excluded because not_finished=True

    def test_filtered_gene_count_is_correct(self):
        """With a disease filter, each study's gene count only includes that disease's cohorts."""
        response = self.client.get(reverse('sickgenes:TableStudy', args=[self.disease_x.id]))
        gene_counts = {study.pk: study.gene_count for study in response.context['table'].data}

        self.assertEqual(gene_counts[self.study1.pk], 1)
        # Study 3 has 2 genes in total, but only 1 in its Disease X cohort
        self.assertEqual(gene_counts[self.study3.pk], 1)

    def test_filter_with_no_results(self):
        """Tests that filtering for a disease with no associated 'finished' studies yields an empty list."""
        # Disease Y is only associated with Study 2, let's mark it as not finished
        self.study2.not_finished = True
        self.study2.save()

        response = self.client.get(reverse('sickgenes:TableStudy', args=[self.disease_y.id]))
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Study 3 should still appear as it has Disease Y cohort
        self.assertIn('Study 3 About Both Diseases', content)
        
        # Study 2 should not appear
        self.assertNotIn('Study 2 About Disease Y', content)

    def search_results(self, search, url=None):
        """Return the studies the study table lists for a search."""
        response = self.client.get(url or self.table_url, {'search': search})
        return set(response.context['table'].data)

    def test_search_matches_title_or_authors(self):
        self.assertEqual(self.search_results('both'), {self.study3})
        self.assertEqual(self.search_results('lewis'), {self.study2})

    def test_search_needs_every_word_to_match(self):
        # Each word can match either field: "Disease" is in the title, "Lewis" in the authors
        self.assertEqual(self.search_results('Disease Lewis'), {self.study2})
        self.assertEqual(self.search_results('Disease nomatch'), set())

    def test_search_combines_with_disease_filter(self):
        url = reverse('sickgenes:TableStudy', args=[self.disease_x.id])
        self.assertEqual(self.search_results('Disease', url), {self.study1, self.study3})

    def test_shortened_author_list_shown(self):
        """Test that view returns shortened author list in et al. format."""
        response = self.client.get(self.table_url)
        self.assertContains(response, 'Smith et al.')

    def test_study_list_page_points_table_at_phenotype_url(self):
        response = self.client.get(self.url, {'phenotype': self.disease_x.id})
        self.assertContains(response, reverse('sickgenes:TableStudy', args=[self.disease_x.id]))
        # Nothing is stored in the session, so other tabs aren't affected
        self.assertNotIn('study_disease_filter', self.client.session)

    def test_study_list_page_without_phenotype_uses_unfiltered_table(self):
        response = self.client.get(self.url)
        self.assertContains(response, f'"{self.table_url}"')

    def test_search_functionality(self):
        """Test that search works on the AJAX endpoint."""
        response = self.client.get(self.table_url, {'search': 'Disease X'})
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode('utf-8')
        
        # Should find Study 1
        self.assertIn('Study 1 About Disease X', content)
        
        # Should not find Study 2
        self.assertNotIn('Study 2 About Disease Y', content)


class ImportHgncTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.out = StringIO()
        cls.start_time = timezone.now()
        call_command('import_molecule_data', 'hgnc', test=True, stdout=cls.out)
        cls.end_time = timezone.now()

    def test_import_hgnc_success_message(self):
        self.assertIn('HGNC data successfully imported', self.out.getvalue())

    def test_hgnc_importer_imports_all_items_from_sample_data(self):
        genes = HgncGene.objects.all()
        self.assertEqual(genes.count(), 3)

    def test_all_hgnc_fields_are_saved(self):
        gene = HgncGene.objects.get(hgnc_id=5)

        self.assertEqual(gene.symbol, 'A1BG')
        self.assertEqual(gene.name, 'alpha-1-B glycoprotein')
        self.assertEqual(gene.entrez_id, 1)
        self.assertEqual(gene.ensembl_gene_id, "ENSG00000121410")
        self.assertEqual(gene.vega_id, "OTTHUMG00000183507")
        self.assertEqual(gene.ucsc_id, "uc002qsd.5")
        self.assertCountEqual([ena.value for ena in gene.ena_set.all()], ['fake_ena'])
        self.assertCountEqual([uniprot_id.value for uniprot_id in gene.uniprotid_set.all()], ["P04217"])
        self.assertCountEqual([omim_id.value for omim_id in gene.omimid_set.all()], [138670])
        self.assertCountEqual([alias_symbol.value for alias_symbol in gene.aliassymbol_set.all()], ['fake_alias_symbol'])
        self.assertCountEqual([alias_name.value for alias_name in gene.aliasname_set.all()], ['fake1', 'fake2'])
        self.assertCountEqual([prev_name.value for prev_name in gene.prevname_set.all()], ['fake_prev_name'])
        self.assertCountEqual([prev_symbol.value for prev_symbol in gene.prevsymbol_set.all()], ['fake_prev_symbol', 'string, including comma'])

    def test_datetime_field_is_recent(self):
        gene = HgncGene.objects.get(hgnc_id=5)

        self.assertGreaterEqual(gene.created_at, self.start_time)
        self.assertLessEqual(gene.created_at, self.end_time)

    def test_update_or_create_behavior(self):
        initial_count = HgncGene.objects.count()

        out = StringIO()
        call_command('import_molecule_data', 'hgnc', test=True, stdout=out)

        self.assertEqual(HgncGene.objects.count(), initial_count)

class ImportHmdbTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.out = StringIO()
        cls.start_time = timezone.now()
        call_command('import_molecule_data', 'hmdb', test=True, stdout=cls.out)
        cls.end_time = timezone.now()

    def test_import_hmdb_success_message(self):
        self.assertIn('HMDB data successfully imported', self.out.getvalue())

    def test_hmdb_importer_imports_all_items_from_sample_data(self):
        molecules = HmdbMetabolite.objects.all()
        # You'll need to adjust this count based on your actual sample HMDB test data
        self.assertEqual(molecules.count(), 3) 

    def test_long_iupac_name_does_not_save(self):
        molecule = HmdbMetabolite.objects.get(accession='HMDB0000002')
        self.assertEqual(molecule.iupac_name, None)

    def test_all_hmdb_fields_are_saved(self):
        molecule = HmdbMetabolite.objects.get(accession='HMDB0000005')

        self.assertEqual(molecule.name, '2-Ketobutyric acid')
        self.assertEqual(molecule.cas_registry_number, '600-18-0')
        self.assertEqual(molecule.drugbank_id, 'DB04553')
        self.assertEqual(molecule.foodb_id, 'FDB030356')
        self.assertEqual(molecule.knapsack_id, 'C00019675')
        self.assertEqual(molecule.biocyc_id, '2-OXOBUTANOATE')
        self.assertEqual(molecule.wikipedia_id, 'Alpha-Ketobutyric_acid')
        self.assertEqual(molecule.bigg_id, 33889)
        self.assertEqual(molecule.pubchem_compound_id, 58)
        self.assertEqual(molecule.chemspider_id, 57)
        self.assertEqual(molecule.chebi_id, 30831)
        self.assertCountEqual([secondary_accession.value for secondary_accession in molecule.secondary_accessions.all()], ['HMDB00005', 'HMDB0006544', 'HMDB06544'])
        self.assertCountEqual([synonym.value for synonym in molecule.synonyms.all()], [
            '2-Ketobutanoic acid', '2-Oxobutyric acid', '3-Methyl pyruvic acid',
            'alpha-Ketobutyrate', 'alpha-Ketobutyric acid', 'alpha-oxo-N-Butyric acid',
            '2-Oxobutyrate', '2-Oxobutanoic acid', '2-Ketobutanoate', '3-Methyl pyruvate',
            'a-Ketobutyrate', 'a-Ketobutyric acid', 'Α-ketobutyrate', 'Α-ketobutyric acid',
            'a-oxo-N-Butyrate', 'a-oxo-N-Butyric acid', 'alpha-oxo-N-Butyrate',
            'Α-oxo-N-butyrate', 'Α-oxo-N-butyric acid', '2-Oxobutanoate',
            '2-Ketobutyrate', '2-oxo-Butanoate', '2-oxo-Butanoic acid',
            '2-oxo-Butyrate', '2-oxo-Butyric acid', '2-oxo-N-Butyrate',
            '2-oxo-N-Butyric acid', '3-Methylpyruvate', '3-Methylpyruvic acid',
            'a-Keto-N-butyrate', 'a-Keto-N-butyric acid', 'a-Oxobutyrate',
            'a-Oxobutyric acid', 'alpha-Keto-N-butyrate', 'alpha-Keto-N-butyric acid',
            'alpha-Ketobutric acid', 'alpha-Oxobutyrate', 'alpha-Oxobutyric acid',
            'Methyl-pyruvate', 'Methyl-pyruvic acid', 'Propionyl-formate',
            'Propionyl-formic acid', 'alpha-Ketobutyric acid, sodium salt',
            '2-Ketobutyric acid'
        ])
        self.assertEqual(molecule.iupac_name, '2-oxobutanoic acid')
        self.assertEqual(molecule.traditional_iupac, '2-oxobutanoic acid')

    def test_datetime_field_is_recent(self):
        molecule = HmdbMetabolite.objects.get(accession='HMDB0000005')

        self.assertGreaterEqual(molecule.created_at, self.start_time)
        self.assertLessEqual(molecule.created_at, self.end_time)

    def test_update_or_create_behavior(self):
        initial_count = HmdbMetabolite.objects.count()

        out = StringIO()
        call_command('import_molecule_data', 'hmdb', test=True, stdout=out)

        self.assertEqual(HmdbMetabolite.objects.count(), initial_count)




class FindMatchingHgncGenesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Gene 1 with various associated fields
        cls.gene1 = HgncGene.objects.create(
            hgnc_id=1,
            symbol="G1",
            name="gene one",
            entrez_id="101",
            ensembl_gene_id="ENSG0000001",
            vega_id="VEGA:1",
            ucsc_id="ucsc1",
        )
        Ena.objects.create(gene=cls.gene1, value="ENA123")
        UniprotId.objects.create(gene=cls.gene1, value="P123")
        UniprotId.objects.create(gene=cls.gene1, value="P456")
        OmimId.objects.create(gene=cls.gene1, value=123)
        OmimId.objects.create(gene=cls.gene1, value=456)
        AliasSymbol.objects.create(gene=cls.gene1, value="G1-ALIAS")
        AliasName.objects.create(gene=cls.gene1, value="One Gene Alias")
        PrevSymbol.objects.create(gene=cls.gene1, value="G1_PREV")
        PrevName.objects.create(gene=cls.gene1, value="Previous Gene One Name")

        # Gene 2 with some shared and unique fields
        cls.gene2 = HgncGene.objects.create(
            hgnc_id=2,
            symbol="G2",
            name="gene two",
            entrez_id="102",
            ensembl_gene_id="ENSG0000002",
            vega_id="VEGA:2",
            ucsc_id="ucsc2",
        )
        OmimId.objects.create(gene=cls.gene2, value=123) # Shared OMIM ID
        OmimId.objects.create(gene=cls.gene2, value=789)
        UniprotId.objects.create(gene=cls.gene2, value='item, comma') # Test for comma in search string

        # Gene 3 for specific field tests
        cls.gene3 = HgncGene.objects.create(
            hgnc_id=3,
            symbol="G3",
            name="gene three",
            entrez_id="103",
        )


    def search_genes(self, search_strings):
        return HgncGene.objects.find_matching_items(search_strings)

    def test_query_count_does_not_grow_with_number_of_search_strings(self):
        with CaptureQueriesContext(connection) as few:
            self.search_genes(['G1', '2'])
        with CaptureQueriesContext(connection) as many:
            self.search_genes(['G1', '2'] + [f'NOTHING{i}' for i in range(10)] + [str(i) for i in range(500, 510)])
        self.assertEqual(len(few), len(many))

    def test_long_search_list_is_fast(self):
        search_strings = [f'NOTHING{i}' for i in range(20000)] + ['G1']
        start = time.time()
        results = self.search_genes(search_strings)
        self.assertLess(time.time() - start, 5)
        self.assertEqual(results['one_match'][0]['item'], self.gene1)

    def test_search_is_case_insensitive_and_keeps_original_string(self):
        results = self.search_genes(['g3'])
        self.assertEqual(results['one_match'], [{'search_string': 'g3', 'item': self.gene3}])

    def test_search_no_matches(self):
        results = self.search_genes(['NOTHING'])
        self.assertIn('NOTHING', results['no_matches'])
        self.assertEqual(len(results['one_match']), 0)
        self.assertEqual(len(results['multiple_matches']), 0)

    # Test individual plain string fields
    def test_search_by_hgnc_id(self):
        results = self.search_genes(['1'])
        self.assertEqual(len(results['one_match']), 1)
        self.assertEqual(results['one_match'][0]['item'], self.gene1)
        results_case_insensitive = self.search_genes(['1'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.gene1)

    def test_search_by_symbol(self):
        results = self.search_genes(['G1'])
        self.assertEqual(results['one_match'][0]['item'], self.gene1)
        results_case_insensitive = self.search_genes(['g1'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.gene1)

    def test_search_by_name(self):
        results = self.search_genes(['gene one'])
        self.assertEqual(results['one_match'][0]['item'], self.gene1)
        results_case_insensitive = self.search_genes(['Gene One'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.gene1)

    def test_search_by_entrez_id(self):
        results = self.search_genes(['101'])
        self.assertEqual(results['one_match'][0]['item'], self.gene1)

    def test_search_by_ensembl_gene_id(self):
        results = self.search_genes(['ENSG0000001'])
        self.assertEqual(results['one_match'][0]['item'], self.gene1)
        results_case_insensitive = self.search_genes(['ensg0000001'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.gene1)

    def test_search_by_vega_id(self):
        results = self.search_genes(['VEGA:1'])
        self.assertEqual(results['one_match'][0]['item'], self.gene1)
        results_case_insensitive = self.search_genes(['vega:1'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.gene1)

    def test_search_by_ucsc_id(self):
        results = self.search_genes(['ucsc1'])
        self.assertEqual(results['one_match'][0]['item'], self.gene1)
        results_case_insensitive = self.search_genes(['UCSC1'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.gene1)

    # Test associated string fields
    def test_search_by_ena_value(self):
        results = self.search_genes(['ENA123'])
        self.assertEqual(results['one_match'][0]['item'], self.gene1)
        results_case_insensitive = self.search_genes(['ena123'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.gene1)

    def test_search_by_uniprot_id_value(self):
        results = self.search_genes(['P123'])
        self.assertEqual(results['one_match'][0]['item'], self.gene1)
        results_case_insensitive = self.search_genes(['p123'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.gene1)

    def test_search_by_alias_symbol_value(self):
        results = self.search_genes(['G1-ALIAS'])
        self.assertEqual(results['one_match'][0]['item'], self.gene1)
        results_case_insensitive = self.search_genes(['g1-alias'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.gene1)

    def test_search_by_alias_name_value(self):
        results = self.search_genes(['One Gene Alias'])
        self.assertEqual(results['one_match'][0]['item'], self.gene1)
        results_case_insensitive = self.search_genes(['one gene alias'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.gene1)

    def test_search_by_prev_symbol_value(self):
        results = self.search_genes(['G1_PREV'])
        self.assertEqual(results['one_match'][0]['item'], self.gene1)
        results_case_insensitive = self.search_genes(['g1_prev'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.gene1)

    def test_search_by_prev_name_value(self):
        results = self.search_genes(['Previous Gene One Name'])
        self.assertEqual(results['one_match'][0]['item'], self.gene1)
        results_case_insensitive = self.search_genes(['previous gene one name'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.gene1)

    # Test associated integer fields
    def test_search_by_omim_id_value(self):
        results = self.search_genes(['456'])
        self.assertEqual(results['one_match'][0]['item'], self.gene1)

    # Test multiple matches
    def test_search_multiple_matches_by_shared_omim(self):
        results = self.search_genes(['123'])
        self.assertEqual(len(results['multiple_matches']), 1)
        matched_items = results['multiple_matches'][0]['items']
        self.assertCountEqual(matched_items, [self.gene1, self.gene2]) # Use assertCountEqual for order-independent check

    # Test special characters in search string
    def test_search_item_with_comma_in_uniprot_id(self):
        results = self.search_genes(['item, comma'])
        self.assertEqual(results['one_match'][0]['item'], self.gene2)


class FindMatchingHmdbMetabolitesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.metabolite1 = HmdbMetabolite.objects.create(
            accession="HMDB0000001",
            name="1-Methylhistidine",
            cas_registry_number="123-45-6",
            drugbank_id="DB001",
            foodb_id="FDB001",
            knapsack_id="KNAP001",
            biocyc_id="BIOCYC001",
            wikipedia_id="Wikipedia_Metabolite_1",
            iupac_name="IUPAC Name One",
            traditional_iupac="Traditional IUPAC One",
            bigg_id=1,
            pubchem_compound_id=101,
            chemspider_id=1001,
            chebi_id=50212,
        )
        MetaboliteSynonym.objects.create(metabolite=cls.metabolite1, value="(2S)-2-amino-3-(1-methyl-1H-imidazol-4-yl)propanoic acid")
        MetaboliteSynonym.objects.create(metabolite=cls.metabolite1, value="Pi-methylhistidine")
        SecondaryAccession.objects.create(metabolite=cls.metabolite1, value="SECACC001")

        cls.metabolite2 = HmdbMetabolite.objects.create(
            accession="HMDB0000002",
            name="2-Methylhistidine",
            cas_registry_number="789-01-2",
            drugbank_id="DB002",
            foodb_id="FDB002",
            knapsack_id="KNAP002",
            biocyc_id="BIOCYC002",
            wikipedia_id="Wikipedia_Metabolite_2",
            iupac_name="IUPAC Name Two",
            traditional_iupac="Traditional IUPAC Two",
            bigg_id=2,
            pubchem_compound_id=102,
            chemspider_id=1002,
            chebi_id=50212, # Shared Chebi ID
        )
        MetaboliteSynonym.objects.create(metabolite=cls.metabolite2, value="(2S)-2-amino-3-(2-methyl-1H-imidazol-4-yl)propanoic acid")
        MetaboliteSynonym.objects.create(metabolite=cls.metabolite2, value="Tau-methylhistidine")
        SecondaryAccession.objects.create(metabolite=cls.metabolite2, value="SECACC002")


    def search_metabolites(self, search_strings):
        return HmdbMetabolite.objects.find_matching_items(search_strings)

    def test_search_no_matches(self):
        results = self.search_metabolites(['NOT_FOUND'])
        self.assertIn('NOT_FOUND', results['no_matches'])
        self.assertEqual(len(results['one_match']), 0)
        self.assertEqual(len(results['multiple_matches']), 0)

    # Test individual plain string fields
    def test_search_by_accession(self):
        results = self.search_metabolites(['HMDB0000001'])
        self.assertEqual(len(results['one_match']), 1)
        self.assertEqual(results['one_match'][0]['item'], self.metabolite1)
        results_case_insensitive = self.search_metabolites(['hmdb0000001'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.metabolite1)

    def test_search_by_name(self):
        results = self.search_metabolites(['1-Methylhistidine'])
        self.assertEqual(results['one_match'][0]['item'], self.metabolite1)
        results_case_insensitive = self.search_metabolites(['1-methylhistidine'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.metabolite1)

    def test_search_by_cas_registry_number(self):
        results = self.search_metabolites(['123-45-6'])
        self.assertEqual(results['one_match'][0]['item'], self.metabolite1)
        results_case_insensitive = self.search_metabolites(['123-45-6'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.metabolite1)

    def test_search_by_drugbank_id(self):
        results = self.search_metabolites(['DB001'])
        self.assertEqual(results['one_match'][0]['item'], self.metabolite1)
        results_case_insensitive = self.search_metabolites(['db001'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.metabolite1)

    def test_search_by_foodb_id(self):
        results = self.search_metabolites(['FDB001'])
        self.assertEqual(results['one_match'][0]['item'], self.metabolite1)
        results_case_insensitive = self.search_metabolites(['fdb001'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.metabolite1)

    def test_search_by_knapsack_id(self):
        results = self.search_metabolites(['KNAP001'])
        self.assertEqual(results['one_match'][0]['item'], self.metabolite1)
        results_case_insensitive = self.search_metabolites(['knap001'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.metabolite1)

    def test_search_by_biocyc_id(self):
        results = self.search_metabolites(['BIOCYC001'])
        self.assertEqual(results['one_match'][0]['item'], self.metabolite1)
        results_case_insensitive = self.search_metabolites(['biocyc001'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.metabolite1)

    def test_search_by_wikipedia_id(self):
        results = self.search_metabolites(['Wikipedia_Metabolite_1'])
        self.assertEqual(results['one_match'][0]['item'], self.metabolite1)
        results_case_insensitive = self.search_metabolites(['wikipedia_metabolite_1'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.metabolite1)

    def test_search_by_iupac_name(self):
        results = self.search_metabolites(['IUPAC Name One'])
        self.assertEqual(results['one_match'][0]['item'], self.metabolite1)
        results_case_insensitive = self.search_metabolites(['iupac name one'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.metabolite1)

    def test_search_by_traditional_iupac(self):
        results = self.search_metabolites(['Traditional IUPAC One'])
        self.assertEqual(results['one_match'][0]['item'], self.metabolite1)
        results_case_insensitive = self.search_metabolites(['traditional iupac one'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.metabolite1)

    # Test associated string fields
    def test_search_by_synonym_value(self):
        results = self.search_metabolites(['Pi-methylhistidine'])
        self.assertEqual(results['one_match'][0]['item'], self.metabolite1)
        results_case_insensitive = self.search_metabolites(['pi-methylhistidine'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.metabolite1)

    def test_search_by_secondary_accession_value(self):
        results = self.search_metabolites(['SECACC001'])
        self.assertEqual(results['one_match'][0]['item'], self.metabolite1)
        results_case_insensitive = self.search_metabolites(['secacc001'])
        self.assertEqual(results_case_insensitive['one_match'][0]['item'], self.metabolite1)

    # Test integer fields
    def test_search_by_bigg_id(self):
        results = self.search_metabolites(['1'])
        self.assertEqual(results['one_match'][0]['item'], self.metabolite1)

    def test_search_by_pubchem_compound_id(self):
        results = self.search_metabolites(['101'])
        self.assertEqual(results['one_match'][0]['item'], self.metabolite1)

    def test_search_by_chemspider_id(self):
        results = self.search_metabolites(['1001'])
        self.assertEqual(results['one_match'][0]['item'], self.metabolite1)

    def test_search_by_chebi_id(self):
        results = self.search_metabolites(['50212'])
        self.assertEqual(len(results['multiple_matches']), 1)
        matched_items = results['multiple_matches'][0]['items']
        self.assertCountEqual(matched_items, [self.metabolite1, self.metabolite2])

    def test_complex_search_hmdb(self):
        results = self.search_metabolites(['HMDB0000002', '50212', 'invalid_search_term'])
        self.assertIn('invalid_search_term', results['no_matches'])
        
        # Check one_match
        self.assertEqual(len(results['one_match']), 1)
        self.assertEqual(results['one_match'][0]['search_string'], 'HMDB0000002')
        self.assertEqual(results['one_match'][0]['item'], self.metabolite2)
        
        # Check multiple_matches
        self.assertEqual(len(results['multiple_matches']), 1)
        self.assertEqual(results['multiple_matches'][0]['search_string'], '50212')
        self.assertCountEqual(results['multiple_matches'][0]['items'], [self.metabolite1, self.metabolite2])

class AddGenesView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.my_admin = User.objects.create_superuser('tesuser', 'myemail@test.com', 'testpassword')

        cls.study = Study.objects.create(title="Example study", doi="https://doi.org/fdfdsa")
        disease = Disease.objects.create(name="ME/CFS")
        cls.study_cohort = StudyCohort.objects.create(study=cls.study)
        cls.study_cohort.disease_tags.add(disease)

    def test_url_valid_response(self):
        self.client.login(username=self.my_admin.username, password='testpassword')
        response = self.client.get(f'/manage/{self.study_cohort.id}/gene/insert/')

        self.assertEqual(response.status_code, 200)

    def test_confirm_adds_matched_genes_to_cohort(self):
        gene = HgncGene.objects.create(hgnc_id=1, symbol='IL6', name='interleukin 6')
        self.client.login(username=self.my_admin.username, password='testpassword')
        data = {
            'search_terms': '',
            'confirm_insert': '1',
            'no_matches-TOTAL_FORMS': '0', 'no_matches-INITIAL_FORMS': '0',
            'multiple_matches-TOTAL_FORMS': '0', 'multiple_matches-INITIAL_FORMS': '0',
            'one_match-TOTAL_FORMS': '1', 'one_match-INITIAL_FORMS': '0',
            'one_match-0-search_term': 'IL6', 'one_match-0-item_id': str(gene.id), 'one_match-0-item_string': 'IL6',
        }
        response = self.client.post(reverse('sickgenes:insert_findings', args=(self.study_cohort.id, 'gene')), data)
        self.assertRedirects(response, self.study.get_absolute_url(), fetch_redirect_response=False)
        self.assertTrue(GeneFinding.objects.filter(study_cohort=self.study_cohort, hgnc_gene=gene).exists())

    def test_unknown_cohort_returns_404(self):
        self.client.login(username=self.my_admin.username, password='testpassword')
        response = self.client.get(reverse('sickgenes:insert_findings', args=(999999, "gene")))
        self.assertEqual(response.status_code, 404)

    def test_view_returns_correct_data(self):
        self.client.login(username=self.my_admin.username, password='testpassword')
        response = self.client.get(reverse('sickgenes:insert_findings', args=(self.study_cohort.id,"gene")))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sickgenes/molecule_match.html')
        self.assertContains(response, "Search")

class RemoveGenesView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff_user = User.objects.create_user('staff', password='pw', is_staff=True)
        cls.study = Study.objects.create(title="Example study")
        cls.study_cohort = StudyCohort.objects.create(study=cls.study)
        cls.other_cohort = StudyCohort.objects.create(study=cls.study)
        cls.il6 = HgncGene.objects.create(hgnc_id=1, symbol='IL6')
        cls.ttn = HgncGene.objects.create(hgnc_id=2, symbol='TTN')
        cls.il6_finding = GeneFinding.objects.create(study_cohort=cls.study_cohort, hgnc_gene=cls.il6)
        cls.ttn_finding = GeneFinding.objects.create(study_cohort=cls.study_cohort, hgnc_gene=cls.ttn)
        cls.other_finding = GeneFinding.objects.create(study_cohort=cls.other_cohort, hgnc_gene=cls.il6)
        cls.url = reverse('sickgenes:remove_findings', args=(cls.study_cohort.id,))

    def test_requires_staff(self):
        response = self.client.post(self.url, {'finding': [self.il6_finding.pk]})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(GeneFinding.objects.filter(pk=self.il6_finding.pk).exists())

    def test_lists_cohort_genes(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(self.url)
        self.assertContains(response, f'value="{self.il6_finding.pk}"')
        self.assertContains(response, f'value="{self.ttn_finding.pk}"')
        self.assertNotContains(response, f'value="{self.other_finding.pk}"')

    def test_removes_only_selected_genes_in_this_cohort(self):
        self.client.force_login(self.staff_user)
        # The other cohort's finding is ignored, even if its ID is sent
        response = self.client.post(self.url, {'finding': [self.il6_finding.pk, self.other_finding.pk]})
        self.assertRedirects(response, self.study.get_absolute_url(), fetch_redirect_response=False)
        self.assertFalse(GeneFinding.objects.filter(pk=self.il6_finding.pk).exists())
        self.assertTrue(GeneFinding.objects.filter(pk=self.ttn_finding.pk).exists())
        self.assertTrue(GeneFinding.objects.filter(pk=self.other_finding.pk).exists())
        self.assertEqual([str(m) for m in get_messages(response.wsgi_request)], ['Removed 1 gene: IL6'])

    def test_study_page_links_to_removal_for_staff(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(self.study.get_absolute_url())
        self.assertContains(response, self.url)


class HiddenStudies(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff_user = User.objects.create_user('staff', password='pw', is_staff=True)
        cls.hidden = Study.objects.create(
            title="Hidden study", doi='10.1000/hidden', not_finished=True, note='No usable genes.'
        )
        cls.public = Study.objects.create(title="Public study")
        cls.publish_url = reverse('sickgenes:publish_study', args=(cls.hidden.pk,))

    def test_list_shows_only_hidden_studies(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('sickgenes:hidden_studies'))
        self.assertContains(response, 'Hidden study')
        self.assertContains(response, 'No usable genes.')
        self.assertNotContains(response, 'Public study')

    def test_list_requires_staff(self):
        response = self.client.get(reverse('sickgenes:hidden_studies'))
        self.assertEqual(response.status_code, 302)

    def test_study_page_shows_publish_button(self):
        self.client.force_login(self.staff_user)
        self.assertContains(self.client.get(self.hidden.get_absolute_url()), self.publish_url)
        public_url = reverse('sickgenes:publish_study', args=(self.public.pk,))
        self.assertNotContains(self.client.get(self.public.get_absolute_url()), public_url)

    def test_publish(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(self.publish_url)
        self.assertRedirects(response, self.hidden.get_absolute_url(), fetch_redirect_response=False)
        self.hidden.refresh_from_db()
        self.assertFalse(self.hidden.not_finished)

    def test_publish_requires_staff_and_post(self):
        self.client.post(self.publish_url)
        self.client.force_login(self.staff_user)
        self.assertEqual(self.client.get(self.publish_url).status_code, 405)
        self.hidden.refresh_from_db()
        self.assertTrue(self.hidden.not_finished)

    def test_add_study_links_to_existing_doi(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(reverse('sickgenes:add_study'), {
            'doi': 'https://doi.org/10.1000/hidden', 'title': 'Again',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.hidden.get_absolute_url())
        self.assertContains(response, '(hidden)')


class AddStudyView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.my_admin = User.objects.create_superuser('tesuser', 'myemail@test.com', 'testpassword')

    def test_url_valid_response(self):
        self.client.login(username=self.my_admin.username, password='testpassword')
        response = self.client.get('/manage/add_study/')

        self.assertEqual(response.status_code, 200)

    def test_add_study_view_get(self):
        self.client.login(username=self.my_admin.username, password='testpassword')
        response = self.client.get(reverse('sickgenes:add_study'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sickgenes/add_study.html')
        self.assertIn('form', response.context)

    def test_add_study_view_post_success(self):
        self.client.login(username=self.my_admin.username, password='testpassword')
        form_data = {
            'doi': '10.1000/xyz123',
            'title': 'A Valid Study',
            'authors': 'Test, Author',
            'publication_year': 2023,
        }
        response = self.client.post(reverse('sickgenes:add_study'), data=form_data)
        self.assertEqual(response.status_code, 302)
        
        self.assertTrue(Study.objects.filter(title='A Valid Study').exists())
        study = Study.objects.get(title='A Valid Study')
        self.assertRedirects(response, study.get_absolute_url())

    def test_add_study_view_post_invalid(self):
        self.client.login(username=self.my_admin.username, password='testpassword')
        form_data = {'title': ''}
        response = self.client.post(reverse('sickgenes:add_study'), data=form_data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sickgenes/add_study.html')
        self.assertTrue(response.context['form'].errors)

    def test_add_study_creates_correct_slug(self):
        self.client.login(username=self.my_admin.username, password='testpassword')
        form_data = {
            'doi': '10.1000/xyz123',
            'title': 'A Valid Study',
            'authors': 'Test, Author',
            'publication_year': 2023,
        }
        self.client.post(reverse('sickgenes:add_study'), data=form_data)
        
        study = Study.objects.get(title='A Valid Study')

        self.assertEqual('a-valid-study-2023', study.slug)

class StudyFormTest(TestCase):

    def test_form_is_valid_with_all_data(self):
        form_data = {
            'doi': '10.1000/xyz123',
            'title': 'Test Title',
            'authors': 'Doe, John',
            'publication_year': 2023,
            'publication_month': 10,
            'publication_day': 26,
            'journal_titles': 'Frontiers in Medicine',
            'publisher_url': 'https://example.com',
            's4me_url': 'https://example.com/s4me',
            'preprint': False,
        }
        form = StudyForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_year_is_required_for_month(self):
        form_data = {'publication_month': 10}
        form = StudyForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('publication_month', form.errors)

    def test_month_is_required_for_day(self):
        form_data = {'publication_day': 26}
        form = StudyForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('publication_day', form.errors)

    def test_invalid_date_combination(self):
        form_data = {
            'publication_year': 2023,
            'publication_month': 2,
            'publication_day': 30,
        }
        form = StudyForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('publication_day', form.errors)

    def test_clean_publication_fields(self):
        form_data = {
            'title': 'Test Title',
            'authors': 'Doe, John',
            'publication_year': 0,
            'publication_month': 0,
            'publication_day': 0,
        }
        form = StudyForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data['publication_year'])
        self.assertIsNone(form.cleaned_data['publication_month'])
        self.assertIsNone(form.cleaned_data['publication_day'])

class FetchPaperInfoViewTest(TestCase):
    def setUp(self):
        staff = User.objects.create_user('staffuser', password='testpassword', is_staff=True)
        self.client.force_login(staff)

    def test_fetch_paper_info_requires_staff(self):
        self.client.logout()
        response = self.client.get(reverse('sickgenes:fetch_paper_info'), {'doi': '10.1000/xyz'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    @patch('sickgenes.views.doi_lookup.requests.get')
    def test_fetch_paper_info_success(self, mock_requests_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'ok',
            'message': {
                'title': ['Test Title from API'],
                'author': [{'given': 'John', 'family': 'Doe'}],
                'issued': {'date-parts': [[2023, 10, 26]]},
                'resource': {'primary': {'URL': 'https://api.example.com'}}
            }
        }
        mock_requests_get.return_value = mock_response

        url = reverse('sickgenes:fetch_paper_info')
        response = self.client.get(url, {'doi': '10.1000/xyz123'})

        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertTrue(json_response['success'])
        self.assertEqual(json_response['title'], 'Test Title from API')
        self.assertEqual(json_response['authors'], 'Doe, John')
        self.assertEqual(json_response['publication_year'], 2023)
        self.assertEqual(json_response['publication_month'], 10)
        self.assertEqual(json_response['publication_day'], 26)
        self.assertEqual(json_response['publisher_url'], 'https://api.example.com')

    @patch('sickgenes.views.doi_lookup.requests.get')
    def test_fetch_paper_info_doi_not_found(self, mock_requests_get):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError
        mock_requests_get.return_value = mock_response

        url = reverse('sickgenes:fetch_paper_info')
        response = self.client.get(url, {'doi': '10.1000/notfound'})
        
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertFalse(json_response['success'])
        self.assertIn('Failed to connect to API', json_response['error'])

    @patch('sickgenes.views.doi_lookup.requests.get')
    def test_fetch_paper_info_api_timeout(self, mock_requests_get):
        # Simulate a timeout
        mock_requests_get.side_effect = requests.exceptions.Timeout

        url = reverse('sickgenes:fetch_paper_info')
        response = self.client.get(url, {'doi': '10.1000/timeout'})
        
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertFalse(json_response['success'])
        self.assertIn('Failed to connect to API', json_response['error'])
        
    def test_fetch_paper_info_missing_doi(self):
        url = reverse('sickgenes:fetch_paper_info')
        response = self.client.get(url) # No DOI provided
        
        self.assertEqual(response.status_code, 200)
        json_response = response.json()
        self.assertFalse(json_response['success'])
        self.assertEqual(json_response['error'], 'DOI is missing.')

    @patch('sickgenes.views.doi_lookup.requests.get')
    def test_fetch_paper_info_record_not_ok(self, mock_requests_get):
        mock_requests_get.return_value = Mock(**{'json.return_value': {'status': 'failed'}})
        response = self.client.get(reverse('sickgenes:fetch_paper_info'), {'doi': '10.1000/xyz'})
        self.assertEqual(response.json(), {'success': False, 'error': 'No data found for this DOI.'})


class ParseCrossrefWorkTest(SimpleTestCase):
    def test_full_record(self):
        work = {
            'title': ['A study'],
            'author': [
                {'given': 'John', 'family': 'Doe'},
                {'family': 'Smith'},
                {'given': 'Ana'},
                {'name': 'A consortium'},  # no given or family name: left out
            ],
            'issued': {'date-parts': [[2023, 10, 26]]},
            'container-title': ['Journal A', 'Journal B'],
            'resource': {'primary': {'URL': 'https://example.com/paper'}},
        }
        self.assertEqual(parse_crossref_work(work), {
            'title': 'A study',
            'authors': 'Doe, John; Smith; Ana',
            'publication_year': 2023,
            'publication_month': 10,
            'publication_day': 26,
            'journal_titles': 'Journal A; Journal B',
            'publisher_url': 'https://example.com/paper',
        })

    def test_year_only(self):
        fields = parse_crossref_work({'issued': {'date-parts': [[2021]]}})
        self.assertEqual(
            (fields['publication_year'], fields['publication_month'], fields['publication_day']),
            (2021, None, None),
        )

    def test_empty_record(self):
        # Crossref sometimes sends an empty title list, or no date at all
        self.assertEqual(parse_crossref_work({'title': [], 'issued': {'date-parts': [[None]]}}), {
            'title': '',
            'authors': '',
            'publication_year': None,
            'publication_month': None,
            'publication_day': None,
            'journal_titles': '',
            'publisher_url': '',
        })


class StudyView(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.staff_user = User.objects.create_user(username="staff", password="pw", is_staff=True)
        cls.normal_user = User.objects.create_user(username="normal", password="pw")

        study = Study.objects.create(title="Example study", doi="https://doi.org/fdfdsa", note="Note with *markdown*")
        disease = Disease.objects.create(name="ME/CFS", code="MECFS")
        study_cohort = StudyCohort.objects.create(study=study)
        study_cohort.disease_tags.add(disease)
        cls.gene1 = HgncGene.objects.create(hgnc_id=1, symbol="ABC1")
        cls.gene2 = HgncGene.objects.create(hgnc_id=2, symbol="ABC2")
        GeneFinding.objects.create(study_cohort=study_cohort, hgnc_gene=cls.gene1)
        GeneFinding.objects.create(study_cohort=study_cohort, hgnc_gene=cls.gene2)
        cls.study_id = study.id

        cls.unfinished_study = Study.objects.create(
            title="Unfinished study",
            doi="https://doi.org/unfinished",
            not_finished=True,
        )
        cls.unfinished_study_id = cls.unfinished_study.id

    def test_url_valid_response(self):
        response = self.client.get(f'/study/{self.study_id}/')

        self.assertEqual(response.status_code, 200)

    def test_random_slug_url_valid_response(self):
        response = self.client.get(f'/study/abc.{self.study_id}/')

        self.assertEqual(response.status_code, 200)

    def test_view_returns_correct_data(self):
        response = self.client.get(reverse('sickgenes:study', args=(self.study_id,)))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sickgenes/study.html')
        self.assertContains(response, "Example study")
        self.assertContains(response, "ME/CFS")

    def test_gene_search_link_uses_cohort_id(self):
        response = self.client.get(reverse('sickgenes:study', args=(self.study_id,)))
        cohort = response.context['study'].study_cohorts.first()
        self.assertContains(response, f"{reverse('sickgenes:gene_list')}?cohort={cohort.id}")

    def test_study_page_shows_study_counts_and_copy_button(self):
        response = self.client.get(reverse('sickgenes:study', args=(self.study_id,)))
        self.assertContains(response, 'title="Found in 1 study">1</sup>', count=2)
        self.assertContains(response, 'data-genes="ABC1&#10;ABC2"')

    def test_study_view_shows_markdown_note(self):
        response = self.client.get(reverse('sickgenes:study', args=(self.study_id,)))
        self.assertContains(response, "Note with <em>markdown</em>")

    def test_unfinished_study_404_for_anonymous(self):
        response = self.client.get(reverse('sickgenes:study', args=(self.unfinished_study_id,)))
        self.assertEqual(response.status_code, 404)

    def test_unfinished_study_404_for_non_staff_user(self):
        self.client.force_login(self.normal_user)
        response = self.client.get(reverse('sickgenes:study', args=(self.unfinished_study_id,)))
        self.assertEqual(response.status_code, 404)

    def test_unfinished_study_visible_to_staff(self):
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('sickgenes:study', args=(self.unfinished_study_id,)))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unfinished study")

    def test_finished_study_still_visible_to_anonymous(self):
        response = self.client.get(reverse('sickgenes:study', args=(self.study_id,)))
        self.assertEqual(response.status_code, 200)

class AddStudyCohortView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.my_admin = User.objects.create_superuser('tesuser', 'myemail@test.com', 'testpassword')

        cls.study = Study.objects.create(title="Example study", doi="https://doi.org/fdfdsa")
        cls.disease_mecfs = Disease.objects.create(name="ME/CFS", code="MECFS")
        cls.disease_healthy = Disease.objects.create(name="Healthy", code="HEALTHY")
        cls.disease_diabetes = Disease.objects.create(name="Diabetes", code=None)

    def test_url_valid_response(self):
        self.client.login(username=self.my_admin.username, password='testpassword')
        response = self.client.get(f'/manage/add_study_cohort/{self.study.id}/')

        self.assertEqual(response.status_code, 200)

    def test_view_returns_correct_data(self):
        self.client.login(username=self.my_admin.username, password='testpassword')
        response = self.client.get(reverse('sickgenes:add_study_cohort', args=(self.study.id,)))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sickgenes/add_study_cohort.html')
        self.assertContains(response, "Disease tags:")

    def test_post_data_to_add_study_cohort(self):
        self.client.login(username=self.my_admin.username, password='testpassword')
        post_data = {
            'disease_tags': [self.disease_mecfs.id, self.disease_diabetes.id],
        }
        response = self.client.post(reverse('sickgenes:add_study_cohort', args=(self.study.id,)), data=post_data)
        study_cohorts_for_study = StudyCohort.objects.filter(study=self.study)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(study_cohorts_for_study.count(), 1)

        new_study_cohort = study_cohorts_for_study.first()
        saved_disease_tag_ids = [tag.id for tag in new_study_cohort.disease_tags.all()]

        self.assertSetEqual(set(saved_disease_tag_ids), set(post_data['disease_tags']))
        self.assertEqual(str(new_study_cohort), f"[{self.study.title[:20]}]... - [Diabetes, ME/CFS]")



class CriteriaRedirectTest(TestCase):
    def test_old_criteria_url_redirects_to_about(self):
        response = self.client.get('/about/criteria/')
        self.assertRedirects(response, reverse('sickgenes:about'), status_code=301)


class SetNewestVersionModelTest(TestCase):

    def setUp(self):
        self.v1 = Study.objects.create(title="Study V1", publication_year=2020)
        self.v2 = Study.objects.create(title="Study V2", publication_year=2021)
        self.v3 = Study.objects.create(title="Study V3", publication_year=2022)

    def test_set_newest_version_updates_direct_predecessor(self):
        self.v2.set_newest_version(self.v3)
        self.v2.refresh_from_db()
        self.assertEqual(self.v2.newest_version, self.v3)

    def test_set_newest_version_updates_ancestors(self):
        """When B->C is set, A (which pointed to B) should now point to C."""
        self.v1.newest_version = self.v2
        self.v1.save()
        self.v2.set_newest_version(self.v3)
        self.v1.refresh_from_db()
        self.assertEqual(self.v1.newest_version, self.v3)

    def test_set_newest_version_does_not_affect_unrelated_studies(self):
        unrelated = Study.objects.create(title="Unrelated", publication_year=2020)
        self.v2.set_newest_version(self.v3)
        unrelated.refresh_from_db()
        self.assertIsNone(unrelated.newest_version)

    def test_set_newest_version_self_is_none(self):
        self.v1.set_newest_version(self.v1)
        self.v1.refresh_from_db()
        self.assertEqual(self.v1.newest_version, None)


class SetNewestVersionFormTest(TestCase):

    def setUp(self):
        self.study = Study.objects.create(title="Study A", publication_year=2020)
        self.other = Study.objects.create(title="Study B", publication_year=2021)

    def test_form_excludes_current_study(self):
        form = SetNewestStudyVersionForm(study=self.study)
        self.assertNotIn(self.study, form.fields['newest_version'].queryset)

    def test_form_includes_other_studies(self):
        form = SetNewestStudyVersionForm(study=self.study)
        self.assertIn(self.other, form.fields['newest_version'].queryset)

    def test_form_valid_with_other_study(self):
        form = SetNewestStudyVersionForm(
            {'newest_version': self.other.pk},
            study=self.study
        )
        self.assertTrue(form.is_valid())


class StudyViewRedirectTest(TestCase):

    def setUp(self):
        self.v1 = Study.objects.create(title="Study V1", publication_year=2020)
        self.v2 = Study.objects.create(title="Study V2", publication_year=2021)
        self.v1.newest_version = self.v2
        self.v1.save()
        self.staff = User.objects.create_user(
            username='staff', password='pass', is_staff=True
        )
        self.user = User.objects.create_user(username='user', password='pass')

    def test_redirects_to_newest_version(self):
        url = reverse('sickgenes:study', kwargs={'study_id': self.v1.pk})
        response = self.client.get(url)
        self.assertRedirects(response, self.v2.get_absolute_url(), fetch_redirect_response=False)

    def test_redirect_includes_message_with_link(self):
        url = reverse('sickgenes:study', kwargs={'study_id': self.v1.pk})
        response = self.client.get(url, follow=True)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn(self.v1.title, str(messages[0]))
        self.assertIn('no_redirect=1', str(messages[0]))

    def test_no_redirect_with_query_param(self):
        url = reverse('sickgenes:study', kwargs={'study_id': self.v1.pk})
        response = self.client.get(url + '?no_redirect=1')
        self.assertEqual(response.status_code, 200)

    def test_no_redirect_if_no_newest_version(self):
        url = reverse('sickgenes:study', kwargs={'study_id': self.v2.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class SetNewestVersionViewTest(TestCase):

    def setUp(self):
        self.v1 = Study.objects.create(title="Study V1", publication_year=2020)
        self.v2 = Study.objects.create(title="Study V2", publication_year=2021)
        self.staff = User.objects.create_user(
            username='staff', password='pass', is_staff=True
        )
        self.user = User.objects.create_user(username='user', password='pass')

    def _post(self, study_id, newest_version_id):
        url = reverse('sickgenes:set_newest_study_version', kwargs={'study_id': study_id})
        return self.client.post(url, {'newest_version': newest_version_id})

    def test_staff_can_set_newest_version(self):
        self.client.login(username='staff', password='pass')
        self._post(self.v1.pk, self.v2.pk)
        self.v1.refresh_from_db()
        self.assertEqual(self.v1.newest_version, self.v2)

    def test_non_staff_cannot_set_newest_version(self):
        self.client.login(username='user', password='pass')
        self._post(self.v1.pk, self.v2.pk)
        self.v1.refresh_from_db()
        self.assertIsNone(self.v1.newest_version)

    def test_anonymous_cannot_set_newest_version(self):
        self._post(self.v1.pk, self.v2.pk)
        self.v1.refresh_from_db()
        self.assertIsNone(self.v1.newest_version)

    def test_redirects_to_study_after_post(self):
        self.client.login(username='staff', password='pass')
        response = self._post(self.v1.pk, self.v2.pk)
        self.assertRedirects(response, self.v1.get_absolute_url(), fetch_redirect_response=False)

    def test_get_request_redirects(self):
        self.client.login(username='staff', password='pass')
        url = reverse('sickgenes:set_newest_study_version', kwargs={'study_id': self.v1.pk})
        response = self.client.get(url)
        self.assertRedirects(response, self.v1.get_absolute_url(), fetch_redirect_response=False)


class PublishedQuerySetTest(TestCase):
    def test_published_leaves_out_hidden_studies_and_older_versions(self):
        current = Study.objects.create(title="Current")
        Study.objects.create(title="Hidden", not_finished=True)
        Study.objects.create(title="Old", newest_version=current)
        self.assertEqual(list(Study.objects.published()), [current])


class RequiredFieldsTest(TestCase):
    """Rows the site can't display (a finding without a gene, a note set to None) can't be saved."""

    def test_gene_finding_needs_a_gene(self):
        study = Study.objects.create(title='Study')
        cohort = StudyCohort.objects.create(study=study)
        with self.assertRaises(IntegrityError):
            GeneFinding.objects.create(study_cohort=cohort)

    def test_gene_needs_an_hgnc_id(self):
        with self.assertRaises(IntegrityError):
            HgncGene.objects.create(symbol='TTN')

    def test_notes_default_to_empty_text(self):
        study = Study.objects.create(title='Study')
        cohort = StudyCohort.objects.create(study=study)
        self.assertEqual(study.note, '')
        self.assertEqual(cohort.note, '')

    def test_saving_a_note_as_none_is_refused(self):
        study = Study.objects.create(title='Study')
        study.note = None
        with self.assertRaises(IntegrityError):
            study.save()


class VisibleToQuerySetTest(TestCase):
    """Hidden studies are for staff only; older versions stay reachable by everyone."""

    @classmethod
    def setUpTestData(cls):
        cls.current = Study.objects.create(title="Current")
        cls.hidden = Study.objects.create(title="Hidden", not_finished=True)
        cls.old = Study.objects.create(title="Old", newest_version=cls.current)

    def test_public_sees_current_and_old_versions_but_not_hidden(self):
        visible = set(Study.objects.visible_to(AnonymousUser()))
        self.assertEqual(visible, {self.current, self.old})

    def test_staff_see_hidden_studies_too(self):
        staff = User(is_staff=True)
        visible = set(Study.objects.visible_to(staff))
        self.assertEqual(visible, {self.current, self.old, self.hidden})


class OldVersionExclusionTest(TestCase):
    """Studies replaced by a newer version are hidden from public lists and counts."""

    def setUp(self):
        gene = HgncGene.objects.create(hgnc_id=12403, symbol='TTN')
        self.v1 = Study.objects.create(title="Old Study", publication_year=2020)
        self.v2 = Study.objects.create(title="New Study", publication_year=2021)
        self.v1.newest_version = self.v2
        self.v1.save()
        for study in (self.v1, self.v2):
            cohort = StudyCohort.objects.create(study=study)
            GeneFinding.objects.create(study_cohort=cohort, hgnc_gene=gene)

    def test_study_table_excludes_old_versions(self):
        response = self.client.get(reverse('sickgenes:TableStudy'))
        studies = list(response.context['table'].data)
        self.assertNotIn(self.v1, studies)
        self.assertIn(self.v2, studies)

    def test_home_excludes_old_versions(self):
        response = self.client.get(reverse('sickgenes:home'))
        self.assertEqual(response.context['study_count'], 1)
        self.assertEqual(list(response.context['recent_studies']), [self.v2])


class RobotsTxtTest(TestCase):
    def test_robots_txt_blocks_paged_gene_list(self):
        response = self.client.get('/robots.txt')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain')
        self.assertContains(response, 'Disallow: /genes/?')


class GeneSearchFormTest(TestCase):
    url = '/search/identify/gene/'
    management_data = {
        f'{prefix}-{key}': '0'
        for prefix in ('no_matches', 'multiple_matches', 'one_match')
        for key in ('TOTAL_FORMS', 'INITIAL_FORMS')
    }

    def test_too_many_lines_shows_error(self):
        from sickgenes.forms.match_forms import MAX_SEARCH_LINES
        lines = '\n'.join(f'GENE{i}' for i in range(MAX_SEARCH_LINES + 1))
        response = self.client.post(self.url, {'search_terms': lines, **self.management_data})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please search at most')

    def test_submission_missing_formset_fields_does_not_error(self):
        response = self.client.post(self.url, {'search_terms': 'TTN'})
        self.assertEqual(response.status_code, 200)

    def formset_data(self, prefix, rows):
        data = {f'{prefix}-TOTAL_FORMS': str(len(rows)), f'{prefix}-INITIAL_FORMS': '0'}
        for i, row in enumerate(rows):
            data.update({f'{prefix}-{i}-{key}': value for key, value in row.items()})
        return data

    def test_choosing_one_of_several_matches_shows_results(self):
        ttn = HgncGene.objects.create(hgnc_id=1, symbol='TTN', name='titin')
        qars1 = HgncGene.objects.create(hgnc_id=2, symbol='QARS1', name='glutaminyl-tRNA synthetase 1')
        eprs1 = HgncGene.objects.create(hgnc_id=3, symbol='EPRS1', name='glutamyl-prolyl-tRNA synthetase 1')
        PrevSymbol.objects.create(gene=qars1, value='QARS')
        PrevSymbol.objects.create(gene=eprs1, value='QARS')

        # First search: QARS matches two genes, shown with their names
        response = self.client.post(self.url, {'search_terms': 'TTN\nQARS\nNOTAGENE', **self.management_data})
        self.assertContains(response, 'QARS1 – glutaminyl-tRNA synthetase 1')
        self.assertContains(response, 'Several matches')
        self.assertContains(response, 'Not found')

        # Choose QARS1 and remove the unknown term: all resolved, so show results
        data = {
            'search_terms': '',
            **self.formset_data('no_matches', [{'search_term': 'NOTAGENE', 'delete': 'on'}]),
            **self.formset_data('multiple_matches', [{'search_term': 'QARS', 'item_id': str(qars1.id)}]),
            **self.formset_data('one_match', [{'search_term': 'TTN', 'item_id': str(ttn.id), 'item_string': 'TTN – titin'}]),
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, reverse('sickgenes:gene_list') + '?symbol=QARS1,TTN', fetch_redirect_response=False)


class RemovedGraphPagesTest(TestCase):
    def test_graph_urls_are_gone(self):
        self.assertEqual(self.client.get('/graph/display/').status_code, 404)
        self.assertEqual(self.client.get('/graph/retrieve-network/?disease_ids=1').status_code, 404)


class HomeRecentStudiesTest(TestCase):
    def test_home_lists_recent_published_studies_with_genes(self):
        gene = HgncGene.objects.create(hgnc_id=1, symbol='TTN')
        for title, not_finished in [('Published study', False), ('Unfinished study', True)]:
            study = Study.objects.create(title=title, not_finished=not_finished)
            cohort = StudyCohort.objects.create(study=study)
            GeneFinding.objects.create(study_cohort=cohort, hgnc_gene=gene)
        Study.objects.create(title='Study without genes')

        response = self.client.get(reverse('sickgenes:home'))
        self.assertEqual([study.title for study in response.context['recent_studies']], ['Published study'])
        self.assertContains(response, 'Recently added')
