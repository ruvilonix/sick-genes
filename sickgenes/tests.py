from django.test import TestCase, SimpleTestCase
from django.core.management import call_command
from sickgenes.models import Molecule, MoleculeAlias, Finding
from io import StringIO
from django.utils import timezone
from django.urls import reverse
import datetime

'''
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


'''
class AddMoleculeViewTests(SimpleTestCase):
    def test_url_exists_at_correct_location(self):
        response = self.client.get('/manage/add_molecules/')
        self.assertEqual(response.status_code, 200)

    def test_add_molecules_view_returns_correct_content(self):
        response = self.client.get(reverse('sickgenes:add_molecules'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sickgenes/molecule_match.html')
        self.assertContains(response, "Search terms")

class FindMatchingMoleculesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.molecules = [
            Molecule.objects.create(
                hgnc_id='HGNC:1',
                hgnc_symbol="G1",
                hgnc_name="gene one",
                type=Molecule.MoleculeType.GENE,
            ),
            Molecule.objects.create(
                hgnc_id='HGNC:2',
                hgnc_symbol="G2",
                hgnc_name="gene two",
                type=Molecule.MoleculeType.GENE,
            ),
            Molecule.objects.create(
                hmdb_accession='HMDB1',
                hmdb_name="metabolite one",
                type=Molecule.MoleculeType.METABOLITE,
            ),
            Molecule.objects.create(
                hgnc_id='HMDB2',
                hmdb_name="metabolite two",
                type=Molecule.MoleculeType.METABOLITE,
            ),
        ]

        molecule_with_aliases = [
            (cls.molecules[0], ['G1A1', 'G1A2']),
            (cls.molecules[1], ['G1A1', 'G1A3']),
            (cls.molecules[2], ['M1A1', 'M1A2']),
            (cls.molecules[3], ['M2A3', 'G1A2']),
        ]

        for molecule in molecule_with_aliases:
            molecule_aliases = [MoleculeAlias(molecule=molecule[0], alias=alias) for alias in molecule[1]]
            MoleculeAlias.objects.bulk_create(molecule_aliases)

    def search_all_molecule_types(self, search_strings, 
            molecule_types=[
                Molecule.MoleculeType.GENE, 
                Molecule.MoleculeType.METABOLITE,
            ]):
        return Molecule.objects.find_matching_molecules(
            search_strings, 
            molecule_types=molecule_types,
        )  
    
    def test_search_results_structure(self):
        pass
        #finish

    def test_search_none(self):
        search_results = self.search_all_molecule_types([])
        self.assertEqual(len(search_results['no_matches']), 0)
    
    def test_search_one_string_with_no_matches(self):
        search_strings = ['NOTHING']
        
        search_results = self.search_all_molecule_types(search_strings)

        self.assertEqual(len(search_results['no_matches']), 1)
        self.assertEqual(search_results['no_matches'][0], 'NOTHING')

    def test_search_one_string_with_one_molecule_match(self):
        search_strings = ['HGNC:1']

        search_results = self.search_all_molecule_types(search_strings)

        self.assertEqual(len(search_results['one_match']), 1)
        self.assertEqual(len(search_results['no_matches']), 0)
        self.assertEqual(len(search_results['multiple_matches']), 0)
        self.assertEqual(search_results['one_match'][0]['search_string'], 'HGNC:1')
        self.assertEqual(search_results['one_match'][0]['molecule'], self.molecules[0])

    
    def test_search_one_string_with_one_alias_match(self):
        search_strings = ['M2A3']

        search_results = self.search_all_molecule_types(search_strings)

        self.assertEqual(search_results['one_match'][0]['molecule'], self.molecules[3])
    
    def test_search_one_string_with_alias_match_to_two_molecules(self):
        search_strings = ['G1A1']
        expected_ids = {'HGNC:1', 'HGNC:2'}

        search_results = self.search_all_molecule_types(search_strings)
        returned_ids = {mol.hgnc_id for mol in search_results['multiple_matches'][0]['molecules']}

        self.assertEqual(expected_ids, returned_ids)

    def test_search_two_strings_with_same_match(self):
        search_strings = ['M1A1', 'M1A2']
        expected_accessions = ['HMDB1', 'HMDB1']

        search_results = self.search_all_molecule_types(search_strings)
        returned_accessions = [result['molecule'].hmdb_accession for result in search_results['one_match']]

        self.assertEqual(expected_accessions, returned_accessions)

    def test_search_based_on_hgnc_symbol(self):
        search_results = self.search_all_molecule_types(['G1'])
        self.assertEqual(search_results['one_match'][0]['molecule'].hgnc_name, 'gene one')

    
    def test_search_based_on_hgnc_name(self):
        search_results = self.search_all_molecule_types(['gene one'])
        self.assertEqual(search_results['one_match'][0]['molecule'].hgnc_symbol, 'G1')

    def test_search_based_on_hmdb_accession(self):
        search_results = self.search_all_molecule_types(['HMDB1'])
        self.assertEqual(search_results['one_match'][0]['molecule'].hmdb_name, 'metabolite one')

    def test_search_based_on_hmdb_name(self):
        search_results = self.search_all_molecule_types(['metabolite one'])
        self.assertEqual(search_results['one_match'][0]['molecule'].hmdb_accession, 'HMDB1')

    def test_search_various_fields_with_inconsistent_capitalization(self):
        search_results = self.search_all_molecule_types(['Hgnc:1', 'g1', 'GENE one', 'hmdb1', 'metabolite ONE', 'g1a2'])
        num_results_with_multiple_matches = len(search_results['multiple_matches'])
        num_results_with_one_matches = len(search_results['one_match'])
        
        self.assertEqual(num_results_with_multiple_matches, 1)
        self.assertEqual(num_results_with_one_matches, 5)

    def test_search_with_wrong_type(self):
        search_results = self.search_all_molecule_types(['G1'], molecule_types=[Molecule.MoleculeType.METABOLITE])
        self.assertEqual(search_results['no_matches'][0], 'G1')

    def test_search_with_correct_type(self):
        search_results = self.search_all_molecule_types(['G1'], molecule_types=[Molecule.MoleculeType.GENE])
        self.assertEqual(search_results['one_match'][0]['molecule'].hgnc_symbol, 'G1')

    def test_search_with_no_types(self):
        pass
    #TODO finish
    

class MoleculeModelTests(TestCase):
    pass