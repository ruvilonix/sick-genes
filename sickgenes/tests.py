from django.test import TestCase
from django.core.management import call_command
from sickgenes.models import HgncGene, Study, Disease, StudyCohort, HmdbMetabolite
from io import StringIO
from django.utils import timezone
from django.urls import reverse
from sickgenes.forms import StudyForm
from .models import (
    HgncGene, Ena, UniprotId, OmimId, AliasSymbol, AliasName, PrevSymbol, PrevName,
    HmdbMetabolite, MetaboliteSynonym, SecondaryAccession
)
from unittest.mock import patch, Mock
import requests
from django.contrib.auth.models import User

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
        gene = HgncGene.objects.get(hgnc_id='HGNC:5')

        self.assertEqual(gene.symbol, 'A1BG')
        self.assertEqual(gene.name, 'alpha-1-B glycoprotein')
        self.assertEqual(gene.entrez_id, "1")
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
        gene = HgncGene.objects.get(hgnc_id='HGNC:5')

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
            hgnc_id='HGNC:1',
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
            hgnc_id='HGNC:2',
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
            hgnc_id='HGNC:3',
            symbol="G3",
            name="gene three",
            entrez_id="103",
        )


    def search_genes(self, search_strings):
        return HgncGene.objects.find_matching_items(search_strings)

    def test_search_no_matches(self):
        results = self.search_genes(['NOTHING'])
        self.assertIn('NOTHING', results['no_matches'])
        self.assertEqual(len(results['one_match']), 0)
        self.assertEqual(len(results['multiple_matches']), 0)

    # Test individual plain string fields
    def test_search_by_hgnc_id(self):
        results = self.search_genes(['HGNC:1'])
        self.assertEqual(len(results['one_match']), 1)
        self.assertEqual(results['one_match'][0]['item'], self.gene1)
        results_case_insensitive = self.search_genes(['hgnc:1'])
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
        control = Disease.objects.create(name="Healthy")
        cls.study_cohort = StudyCohort.objects.create(study=cls.study)
        cls.study_cohort.disease_tags.add(disease)
        cls.study_cohort.control_tags.add(control)

    def test_url_valid_response(self):
        self.client.login(username=self.my_admin.username, password='testpassword')
        response = self.client.get(f'/manage/{self.study.id}/gene/insert/')

        self.assertEqual(response.status_code, 200)

    def test_view_returns_correct_data(self):
        self.client.login(username=self.my_admin.username, password='testpassword')
        response = self.client.get(reverse('sickgenes:insert_findings', args=(self.study.id,"gene")))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sickgenes/molecule_match.html')
        self.assertContains(response, "Search terms:")

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

class StudyFormTest(TestCase):

    def test_form_is_valid_with_all_data(self):
        form_data = {
            'doi': '10.1000/xyz123',
            'title': 'Test Title',
            'authors': 'Doe, John',
            'publication_year': 2023,
            'publication_month': 10,
            'publication_day': 26,
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

class StudyView(TestCase):
    @classmethod
    def setUpTestData(cls):
        study = Study.objects.create(title="Example study", doi="https://doi.org/fdfdsa")
        disease = Disease.objects.create(name="ME/CFS")
        control = Disease.objects.create(name="Healthy")
        study_cohort = StudyCohort.objects.create(study=study)
        study_cohort.disease_tags.add(disease)
        study_cohort.control_tags.add(control)
        cls.study_id = study.id

    def test_url_valid_response(self):
        response = self.client.get(f'/study/{self.study_id}/')

        self.assertEqual(response.status_code, 200)

    def test_view_returns_correct_data(self):
        response = self.client.get(reverse('sickgenes:study', args=(self.study_id,)))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sickgenes/study.html')
        self.assertContains(response, "Example study")
        self.assertContains(response, "ME/CFS")
        self.assertContains(response, "Healthy")

class AddStudyCohortView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.my_admin = User.objects.create_superuser('tesuser', 'myemail@test.com', 'testpassword')

        cls.study = Study.objects.create(title="Example study", doi="https://doi.org/fdfdsa")
        cls.disease_mecfs = Disease.objects.create(name="ME/CFS")
        cls.disease_healthy = Disease.objects.create(name="Healthy")
        cls.disease_diabetes = Disease.objects.create(name="Diabetes")

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
            'control_tags': [self.disease_healthy.id],
        }
        response = self.client.post(reverse('sickgenes:add_study_cohort', args=(self.study.id,)), data=post_data)
        study_cohorts_for_study = StudyCohort.objects.filter(study=self.study)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(study_cohorts_for_study.count(), 1)

        new_study_cohort = study_cohorts_for_study.first()
        saved_disease_tag_ids = [tag.id for tag in new_study_cohort.disease_tags.all()]
        saved_control_tag_ids = [tag.id for tag in new_study_cohort.control_tags.all()]

        self.assertSetEqual(set(saved_disease_tag_ids), set(post_data['disease_tags']))
        self.assertSetEqual(set(saved_control_tag_ids), set(post_data['control_tags']))