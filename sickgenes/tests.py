from django.test import TestCase, SimpleTestCase
from django.core.management import call_command
from sickgenes.models import HgncGene
from io import StringIO
from django.utils import timezone
from django.urls import reverse

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
        self.assertEqual(gene.ena, ['fake_ena'])
        self.assertEqual(gene.uniprot_ids, ["P04217"])
        self.assertEqual(gene.omim_id, [138670])
        self.assertEqual(gene.alias_symbol, ['fake_alias_symbol'])
        self.assertEqual(gene.alias_name, ['fake1', 'fake2'])
        self.assertEqual(gene.prev_name, ['fake_prev_name'])
        self.assertEqual(gene.prev_symbol, ['fake_prev_symbol', 'string, including comma'])

    def test_datetime_field_is_recent(self):
        gene = HgncGene.objects.get(hgnc_id='HGNC:5')

        self.assertGreaterEqual(gene.datetime_updated, self.start_time)
        self.assertLessEqual(gene.datetime_updated, self.end_time)

    def test_update_or_create_behavior(self):
        initial_count = HgncGene.objects.count()

        out = StringIO()
        call_command('import_molecule_data', 'hgnc', test=True, stdout=out)

        self.assertEqual(HgncGene.objects.count(), initial_count)


class FindMatchingHgncGenesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.genes = [
            HgncGene.objects.create(
                hgnc_id='HGNC:1',
                symbol="G1",
                name="gene one",
                omim_id=[123, 456],
                uniprot_ids=['P123', 'P456'],
            ),
            HgncGene.objects.create(
                hgnc_id='HGNC:2',
                symbol="G2",
                name="gene two",
                omim_id=[123, 789],
                uniprot_ids=['item, comma'],
            )
        ]

    def search_genes(self, search_strings):
        return HgncGene.objects.find_matching_items(search_strings)  

    def test_search_none(self):
        search_results = self.search_genes([])
        self.assertEqual(len(search_results['no_matches']), 0)
    
    def test_search_one_string_with_no_matches(self):
        search_results = self.search_genes(['NOTHING'])

        self.assertEqual(len(search_results['no_matches']), 1)
        self.assertEqual(search_results['no_matches'][0], 'NOTHING')

    def test_search_one_string_with_one_gene_match(self):
        search_results = self.search_genes(['HGNC:1'])

        self.assertEqual(len(search_results['one_match']), 1)
        self.assertEqual(len(search_results['no_matches']), 0)
        self.assertEqual(len(search_results['multiple_matches']), 0)
        self.assertEqual(search_results['one_match'][0]['search_string'], 'HGNC:1')
        self.assertEqual(search_results['one_match'][0]['item'], self.genes[0])
    
    def test_search_one_string_with_one_alias_match(self):
        search_results = self.search_genes(['G2'])

        self.assertEqual(search_results['one_match'][0]['item'], self.genes[1])
    
    def test_search_one_string_with_alias_match_to_two_genes(self):
        expected_ids = {'HGNC:1', 'HGNC:2'}
        search_results = self.search_genes(['123'])
        returned_ids = {gene.hgnc_id for gene in search_results['multiple_matches'][0]['items']}

        self.assertEqual(expected_ids, returned_ids)

    def test_search_exact_in_string_array_field(self):
        search_results = self.search_genes(["P123"])
        self.assertEqual(search_results['one_match'][0]['item'], self.genes[0])

    def test_search_case_insensitive_in_string_array_field(self):
        search_results = self.search_genes(["p123"])
        self.assertEqual(search_results['one_match'][0]['item'], self.genes[0])

    def test_search_item_with_comma(self):
        search_results = self.search_genes(['item, comma'])
        self.assertEqual(search_results['one_match'][0]['item'], self.genes[1])

class AddGenesView(SimpleTestCase):
    def test_url_valid_response(self):
        response = self.client.get('/manage/add_genes/')

        self.assertEqual(response.status_code, 200)

    def test_view_returns_correct_data(self):
        response = self.client.get(reverse('sickgenes:add_genes'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sickgenes/molecule_match.html')
        self.assertContains(response, "Search terms:")