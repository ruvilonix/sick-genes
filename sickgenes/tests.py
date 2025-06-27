from django.test import TestCase, SimpleTestCase
from django.core.management import call_command
from sickgenes.models import Molecule
from io import StringIO
from django.utils import timezone
from django.urls import reverse
import datetime

class ImportHgncTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.out = StringIO()
        call_command('import_molecule_data', 'hgnc', test=True, stdout=cls.out)

    def test_import_hgnc_success_message(self):
        self.assertIn('HGNC data successfully imported', self.out.getvalue())

    def test_hgnc_importer_imports_all_items_from_sample_data(self):
        molecules = Molecule.objects.all()
        self.assertEqual(len(molecules), 3)

    def test_hgnc_import_connects_moleculealias_to_molecule(self):
        molecule = Molecule.objects.get(hgnc_symbol='A1CF')
        molecule_from_alias = Molecule.objects.get(moleculealias__alias='ACF')
        self.assertEqual(molecule, molecule_from_alias)

    def test_all_hgnc_fields_are_saved(self):
        molecule = Molecule.objects.get(hgnc_id='HGNC:5')

        self.assertEqual(molecule.hgnc_symbol, 'A1BG')
        self.assertEqual(molecule.hgnc_name, 'alpha-1-B glycoprotein')
        self.assertEqual(molecule.type, Molecule.MoleculeType.GENE)

    def test_datetime_field_within_past_hour(self):
        molecule = Molecule.objects.get(hgnc_id='HGNC:5')

        self.assertGreaterEqual(molecule.datetime_updated, timezone.now() - datetime.timedelta(hours=1))
        self.assertLessEqual(molecule.datetime_updated, timezone.now())

class ImportHmdbTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.out = StringIO()
        call_command('import_molecule_data', 'hmdb', test=True, stdout=cls.out)
    
    def test_import_hmdb_success_message(self):
        self.assertIn('HMDB data successfully imported', self.out.getvalue())

    def test_hmdb_importer_imports_all_items_from_sample_data(self):
        molecules = Molecule.objects.all()
        self.assertEqual(len(molecules), 3)

    def test_hmdb_import_connects_moleculealias_to_molecule(self):
        molecule = Molecule.objects.get(hmdb_name='1-Methylhistidine')
        molecule_from_alias = Molecule.objects.get(moleculealias__alias='1-MHis')
        self.assertEqual(molecule, molecule_from_alias)

    def test_all_hgnc_fields_are_saved(self):
        molecule = Molecule.objects.get(hmdb_accession='HMDB0000002')

        self.assertEqual(molecule.hmdb_name, '1,3-Diaminopropane')
        self.assertEqual(molecule.type, Molecule.MoleculeType.METABOLITE)

    def test_datetime_field_within_past_hour(self):
        molecule = Molecule.objects.get(hmdb_accession='HMDB0000002')

        self.assertGreaterEqual(molecule.datetime_updated, timezone.now() - datetime.timedelta(hours=1))
        self.assertLessEqual(molecule.datetime_updated, timezone.now())

class AddMoleculeViewTests(SimpleTestCase):
    def test_url_exists_at_correct_location(self):
        response = self.client.get('/manage/add_molecules/')
        self.assertEqual(response.status_code, 200)

    def test_add_molecules_view_returns_correct_content(self):
        response = self.client.get(reverse('sickgenes:add_molecules'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sickgenes/molecule_match.html')
        self.assertContains(response, "Molecule list:")