from django.test import TestCase, SimpleTestCase
from django.core.management import call_command
from sickgenes.models import Molecule, MoleculeAlias, Finding
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

class FindMatchingMoleculesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        molecules = [
            {
                'hgnc_id': 'HGNC:1',
                'hgnc_symbol': 'G1',
                'hgnc_name': 'gene one',
                'type': Molecule.MoleculeType.GENE,
                'aliases': ['G1A1', 'G1A2']
            },
            {
                'hgnc_id': 'HGNC:2',
                'hgnc_symbol': 'G2',
                'hgnc_name': 'gene two',
                'type': Molecule.MoleculeType.GENE,
                'aliases': ['G1A1', 'G1A3']
            },
            {
                'hmdb_accession': 'HMDB1',
                'hmdb_name': 'metabolite one',
                'type': Molecule.MoleculeType.METABOLITE,
                'aliases': ['M1A1', 'M1A2']
            },
            {
                'hmdb_accession': 'HMDB2',
                'hmdb_name': 'metabolite two',
                'type': Molecule.MoleculeType.METABOLITE,
                'aliases': ['M2A3', 'G1A2']
            },
        ]

        for molecule in molecules:
            aliases = molecule.pop('aliases')
            molecule = Molecule.objects.create(**molecule)
            molecule_aliases = [MoleculeAlias(molecule=molecule, alias=alias) for alias in aliases]
            MoleculeAlias.objects.bulk_create(molecule_aliases)

    def search_all_molecule_types(self, search_strings):
        return Molecule.objects.find_matching_molecules(
            search_strings, 
            molecule_types=[
                Molecule.MoleculeType.GENE, 
                Molecule.MoleculeType.METABOLITE,
            ]
        )
            

    def test_search_none(self):
        search_results = self.search_all_molecule_types([])
        self.assertEqual(len(search_results), 0)
        
    def test_search_one_string_with_no_matches(self):
        search_strings = ['NOTHING']
        
        search_results = self.search_all_molecule_types(search_strings)

        self.assertEqual(len(search_results), 1)
        self.assertEqual(search_results[0]['search_string'], 'NOTHING')
        self.assertEqual(len(search_results[0]['molecules']), 0)

    def test_search_one_string_with_one_molecule_match(self):
        search_strings = ['HGNC:1']

        search_results = self.search_all_molecule_types(search_strings)

        self.assertEqual(len(search_results), 1)
        self.assertEqual(search_results[0]['search_string'], 'HGNC:1')
        self.assertEqual(len(search_results[0]['molecules']), 1)

    def test_search_one_string_with_one_alias_match(self):
        search_strings = ['M2A3']
        molecules = Molecule.objects.filter(moleculealias__alias='M2A3')
        molecule = Molecule.objects.get(hmdb_accession='HMDB2')

        search_results = self.search_all_molecule_types(search_strings)

        self.assertEqual(len(search_results), 1)
        self.assertEqual(search_results[0]['search_string'], 'M2A3')
        self.assertQuerySetEqual(search_results[0]['molecules'], molecules)
        self.assertEqual(search_results[0]['molecules'][0], molecule)
    
    def test_search_one_string_with_alias_match_to_two_molecules(self):
        search_strings = ['G1A1']
        molecules = Molecule.objects.filter(moleculealias__alias='G1A1')
        expected_accessions = {'HGNC:1', 'HGNC:2'}

        search_results = self.search_all_molecule_types(search_strings)
        returned_accessions = {mol.hgnc_id for mol in search_results[0]['molecules']}

        self.assertEqual(len(search_results), 1)
        self.assertEqual(len(search_results[0]['molecules']), 2)
        self.assertQuerySetEqual(search_results[0]['molecules'], molecules, ordered=False)
        self.assertEqual(expected_accessions, returned_accessions)

    def test_search_two_strings_with_same_match(self):
        search_strings = ['M1A1', 'M1A2']
        expected_accessions = ['metabolite one', 'metabolite one']

        search_results = self.search_all_molecule_types(search_strings)
        returned_accessions = [mol.hmdb_name for mol in search_results[0]['molecules']]
        returned_accessions += [mol.hmdb_name for mol in search_results[1]['molecules']]

        self.assertEqual(len(search_results), 2)
        self.assertEqual(len(search_results[0]['molecules']), 1)
        self.assertEqual(len(search_results[1]['molecules']), 1)
        self.assertEqual(expected_accessions, returned_accessions)

    def test_search_based_on_hgnc_id(self):
        search_results = self.search_all_molecule_types(['HGNC:1'])
        self.assertEqual(search_results[0]['molecules'][0].hgnc_name, 'gene one')

    def test_search_based_on_hgnc_symbol(self):
        search_results = self.search_all_molecule_types(['G1'])
        self.assertEqual(search_results[0]['molecules'][0].hgnc_name, 'gene one')

    def test_search_based_on_hgnc_name(self):
        search_results = self.search_all_molecule_types(['gene one'])
        self.assertEqual(search_results[0]['molecules'][0].hgnc_symbol, 'G1')

    def test_search_based_on_hmdb_accession(self):
        search_results = self.search_all_molecule_types(['HMDB1'])
        self.assertEqual(search_results[0]['molecules'][0].hmdb_name, 'metabolite one')

    def test_search_based_on_hmdb_name(self):
        search_results = self.search_all_molecule_types(['metabolite one'])
        self.assertEqual(search_results[0]['molecules'][0].hmdb_accession, 'HMDB1')

    def test_search_various_fields_with_inconsistent_capitalization(self):
        search_results = self.search_all_molecule_types(['Hgnc:1', 'g1', 'GENE one', 'hmdb1', 'metabolite ONE', 'g1a2'])
        num_results_per_search_term = [len(result['molecules']) for result in search_results]
        
        self.assertCountEqual(num_results_per_search_term, [1, 1, 1, 1, 1, 2])

class MoleculeModelTests(TestCase):
    pass