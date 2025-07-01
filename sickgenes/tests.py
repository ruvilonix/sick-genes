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
        self.assertEqual(gene.pubmed_id, [2591067])
        self.assertEqual(gene.omim_id, [138670])
        self.assertEqual(gene.alias_symbol, ['fake_alias_symbol'])
        self.assertEqual(gene.alias_name, ['fake1', 'fake2'])
        self.assertEqual(gene.prev_name, ['fake_prev_name'])
        self.assertEqual(gene.prev_symbol, ['fake_prev_symbol'])

    def test_datetime_field_is_recent(self):
        gene = HgncGene.objects.get(hgnc_id='HGNC:5')

        self.assertGreaterEqual(gene.datetime_updated, self.start_time)
        self.assertLessEqual(gene.datetime_updated, self.end_time)

    def test_update_or_create_behavior(self):
        initial_count = HgncGene.objects.count()

        out = StringIO()
        call_command('import_molecule_data', 'hgnc', test=True, stdout=out)

        self.assertEqual(HgncGene.objects.count(), initial_count)
